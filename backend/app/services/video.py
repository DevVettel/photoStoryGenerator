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


def _split_sentence_at_midpoint(sentence: str) -> list[str]:
    mid = len(sentence) // 2
    split_pos = sentence.rfind(' ', 0, mid)
    if split_pos == -1:
        split_pos = mid
    return [sentence[:split_pos].strip(), sentence[split_pos:].strip()]


def _write_srt_entry(f, index: int, start: float, end: float, text: str, total_duration: float) -> None:
    end = min(end, total_duration)
    f.write(f"{index}\n")
    f.write(f"{_format_srt_time(start)} --> {_format_srt_time(end)}\n")
    f.write(f"{text}\n\n")


def _write_simple_srt(srt_path: str, image_count: int, duration_per_image: float) -> None:
    with open(srt_path, "w", encoding="utf-8") as f:
        for i in range(image_count):
            start = i * duration_per_image
            end = (i + 1) * duration_per_image
            f.write(f"{i + 1}\n")
            f.write(f"{_format_srt_time(start)} --> {_format_srt_time(end)}\n")
            f.write(f"Bölüm {i + 1}\n\n")


def _generate_srt(srt_path: str, image_count: int, duration_per_image: float, story_text: str = "") -> None:
    if not story_text:
        _write_simple_srt(srt_path, image_count, duration_per_image)
        return

    sentences = [s.strip() + '.' for s in story_text.replace('\n', ' ').split('.') if len(s.strip()) > 5]
    total_duration = image_count * duration_per_image
    duration_per_sentence = max(1.5, min(total_duration / len(sentences), duration_per_image))

    with open(srt_path, "w", encoding="utf-8") as f:
        current_time = 0.0
        entry_index = 1
        for sentence in sentences:
            if len(sentence) > 80:
                parts = _split_sentence_at_midpoint(sentence)
                part_dur = duration_per_sentence / 2
                for j, part in enumerate(parts):
                    start = current_time + j * part_dur
                    _write_srt_entry(f, entry_index, start, start + part_dur, part, total_duration)
                    entry_index += 1
            else:
                _write_srt_entry(f, entry_index, current_time, current_time + duration_per_sentence, sentence, total_duration)
                entry_index += 1
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

    srt_path = output_path.replace(".mp4", ".srt")
    _generate_srt(srt_path, image_count, duration_per_image, story_text)

    segment_duration = duration_per_image + xfade_duration

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
    xfade_types = ["dissolve", "fadeblack", "smoothleft", "smoothright", "fade"]

    input_args = []
    for img in image_paths:
        input_args += ["-loop", "1", "-t", str(segment_duration), "-i", img]

    filter_parts = []

    for i in range(image_count):
        effect_fn = kb_effects[i % len(kb_effects)]
        kb = effect_fn(segment_duration, fps)
        filter_parts.append(
            f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=increase,"
            f"crop=1920:1080,setsar=1,setpts=PTS-STARTPTS,"
            f"{kb}[kb{i}]"
        )

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
