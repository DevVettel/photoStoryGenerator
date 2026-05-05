import os
import subprocess


def get_audio_duration(audio_path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _generate_srt(srt_path: str, image_count: int, duration_per_image: float, story_text: str = "") -> None:
    if not story_text:
        segments = [
            {"index": i+1, "start": i*duration_per_image, "end": (i+1)*duration_per_image, "text": f"Bölüm {i+1}"}
            for i in range(image_count)
        ]
        with open(srt_path, "w", encoding="utf-8") as f:
            for seg in segments:
                f.write(f"{seg['index']}\n")
                f.write(f"{_format_srt_time(seg['start'])} --> {_format_srt_time(seg['end'])}\n")
                f.write(f"{seg['text']}\n\n")
        return

    # Cümleleri böl
    sentences = [s.strip() + '.' for s in story_text.replace('\n', ' ').split('.') if len(s.strip()) > 5]
    total_duration = image_count * duration_per_image

    # Her cümleye eşit süre ver
    duration_per_sentence = total_duration / len(sentences)
    # Minimum 1.5s, maksimum görsel süresi kadar
    duration_per_sentence = max(1.5, min(duration_per_sentence, duration_per_image))

    with open(srt_path, "w", encoding="utf-8") as f:
        current_time = 0.0
        for i, sentence in enumerate(sentences):
            # Cümle çok uzunsa ikiye böl
            if len(sentence) > 80:
                mid = len(sentence) // 2
                # En yakın boşlukta böl
                split_pos = sentence.rfind(' ', 0, mid)
                if split_pos == -1:
                    split_pos = mid
                parts = [sentence[:split_pos].strip(), sentence[split_pos:].strip()]
                part_dur = duration_per_sentence / 2
                for j, part in enumerate(parts):
                    start = current_time + j * part_dur
                    end = start + part_dur
                    if end > total_duration:
                        end = total_duration
                    f.write(f"{i*2+j+1}\n")
                    f.write(f"{_format_srt_time(start)} --> {_format_srt_time(end)}\n")
                    f.write(f"{part}\n\n")
            else:
                end = current_time + duration_per_sentence
                if end > total_duration:
                    end = total_duration
                f.write(f"{i+1}\n")
                f.write(f"{_format_srt_time(current_time)} --> {_format_srt_time(end)}\n")
                f.write(f"{sentence}\n\n")

            current_time += duration_per_sentence
            if current_time >= total_duration:
                break


def assemble_video(
    audio_path: str,
    image_paths: list[str],
    output_path: str,
    story_text: str = "",
) -> str:
    audio_duration = get_audio_duration(audio_path)
    image_count = len(image_paths)
    duration_per_image = audio_duration / image_count
    fps = 25
    xfade_duration = 1.0

    # SRT oluştur
    srt_path = output_path.replace(".mp4", ".srt")
    _generate_srt(srt_path, image_count, duration_per_image, story_text)

    # Her görsel için gerçek süre (xfade overlap dahil)
    segment_duration = duration_per_image + xfade_duration

    # Ken Burns efektleri — tam segment süresini kapsar
    def kb_zoom_in(d, f):
        n = int(d * f)
        return f"zoompan=z='min(1+on/{n}*0.08\\,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1280x720:fps={f}"

    def kb_zoom_out(d, f):
        n = int(d * f)
        return f"zoompan=z='max(1.08-on/{n}*0.08\\,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1280x720:fps={f}"

    def kb_pan_right(d, f):
        n = int(d * f)
        return f"zoompan=z=1.06:x='iw/2-(iw/zoom/2)+on/{n}*40':y='ih/2-(ih/zoom/2)':d={n}:s=1280x720:fps={f}"

    def kb_pan_left(d, f):
        n = int(d * f)
        return f"zoompan=z=1.06:x='iw/2-(iw/zoom/2)-on/{n}*40+40':y='ih/2-(ih/zoom/2)':d={n}:s=1280x720:fps={f}"

    def kb_pan_up(d, f):
        n = int(d * f)
        return f"zoompan=z=1.06:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)+on/{n}*30':d={n}:s=1280x720:fps={f}"

    kb_effects = [kb_zoom_in, kb_zoom_out, kb_pan_right, kb_pan_left, kb_pan_up]

    # xfade geçiş tipleri
    xfade_types = ["dissolve", "fadeblack", "smoothleft", "smoothright", "fade"]

    # Input argümanları
    input_args = []
    for img in image_paths:
        input_args += ["-loop", "1", "-t", str(segment_duration), "-i", img]

    # Filter complex
    filter_parts = []

    # Adım 1: scale → Ken Burns
    for i in range(image_count):
        effect_fn = kb_effects[i % len(kb_effects)]
        kb = effect_fn(segment_duration, fps)
        filter_parts.append(
            f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=increase,"
            f"crop=1920:1080,setsar=1,setpts=PTS-STARTPTS,"
            f"{kb}[kb{i}]"
        )

    # Adım 2: xfade geçişleri
    if image_count == 1:
        last_label = "kb0"
    else:
        prev_label = "kb0"
        for i in range(1, image_count):
            xfade_type = xfade_types[(i - 1) % len(xfade_types)]
            offset = i * duration_per_image - xfade_duration * 0.5
            out_label = f"xf{i}" if i < image_count - 1 else "xflast"
            filter_parts.append(
                f"[{prev_label}][kb{i}]xfade=transition={xfade_type}"
                f":duration={xfade_duration}:offset={offset:.3f}[{out_label}]"
            )
            prev_label = out_label
        last_label = "xflast"

    # Adım 3: Altyazı
    filter_parts.append(
        f"[{last_label}]subtitles={srt_path}:force_style='FontSize=20\\,PrimaryColour=&Hffffff\\,OutlineColour=&H000000\\,Outline=2\\,Alignment=2\\,Bold=1'[outv]"
    )

    filter_complex = ";".join(filter_parts)

    cmd = (
        input_args
        + ["-i", audio_path]
        + ["-filter_complex", filter_complex]
        + ["-map", "[outv]"]
        + ["-map", f"{image_count}:a"]
        + ["-c:v", "libx264", "-preset", "fast", "-crf", "20"]
        + ["-c:a", "aac", "-b:a", "192k"]
        + ["-r", str(fps)]
        + ["-shortest", "-y", output_path]
    )

    result = subprocess.run(
        ["ffmpeg"] + cmd,
        capture_output=True,
        text=True,
        timeout=600,
    )

    if os.path.exists(srt_path):
        os.remove(srt_path)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası: {result.stderr[-1000:]}")

    return output_path
