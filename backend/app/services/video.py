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


def assemble_video(
    audio_path: str,
    image_paths: list[str],
    output_path: str,
) -> str:
    audio_duration = get_audio_duration(audio_path)
    image_count = len(image_paths)
    duration_per_image = audio_duration / image_count
    fade_duration = 0.5

    # SRT dosyasını önceden oluştur
    srt_path = output_path.replace(".mp4", ".srt")
    _generate_srt(srt_path, image_count, duration_per_image)

    # Her görsel için input argümanları
    input_args = []
    for img in image_paths:
        input_args += ["-loop", "1", "-t", str(duration_per_image + fade_duration), "-i", img]

    # Filter complex: fade + altyazı tek geçişte
    filter_parts = []
    for i in range(image_count):
        fade_in_start = 0
        fade_out_start = duration_per_image - fade_duration
        filter_parts.append(
            f"[{i}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
            f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,fps=30,"
            f"fade=t=in:st={fade_in_start}:d={fade_duration},"
            f"fade=t=out:st={fade_out_start}:d={fade_duration}[v{i}]"
        )

    concat_inputs = "".join([f"[v{i}]" for i in range(image_count)])
    # Altyazıyı concat sonrasına ekle
    filter_parts.append(f"{concat_inputs}concat=n={image_count}:v=1:a=0[concatv]")
    filter_parts.append(
        f"[concatv]subtitles={srt_path}:force_style=FontSize=20[outv]"
    )

    filter_complex = ";".join(filter_parts)

    cmd = (
        input_args
        + ["-i", audio_path]
        + ["-filter_complex", filter_complex]
        + ["-map", "[outv]"]
        + ["-map", f"{image_count}:a"]
        + ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]
        + ["-c:a", "aac", "-b:a", "192k"]
        + ["-shortest", "-y", output_path]
    )

    result = subprocess.run(
        ["ffmpeg"] + cmd,
        capture_output=True,
        text=True,
        timeout=300,
    )

    # SRT'yi temizle
    if os.path.exists(srt_path):
        os.remove(srt_path)

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası: {result.stderr[-500:]}")

    return output_path


def _generate_srt(srt_path: str, image_count: int, duration_per_image: float) -> None:
    """Her görsel için basit zaman damgalı SRT altyazı dosyası oluşturur."""
    labels = [
        "Bölüm 1", "Bölüm 2", "Bölüm 3",
        "Bölüm 4", "Bölüm 5", "Bölüm 6",
    ]

    with open(srt_path, "w", encoding="utf-8") as f:
        for i in range(image_count):
            start = i * duration_per_image
            end = (i + 1) * duration_per_image
            label = labels[i] if i < len(labels) else f"Bölüm {i+1}"

            f.write(f"{i+1}\n")
            f.write(f"{_format_srt_time(start)} --> {_format_srt_time(end)}\n")
            f.write(f"{label}\n\n")


def _format_srt_time(seconds: float) -> str:
    """Saniyeyi SRT zaman formatına çevirir: HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
