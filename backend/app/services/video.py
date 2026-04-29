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

    # Her görsel için input argümanları
    input_args = []
    for img in image_paths:
        input_args += ["-loop", "1", "-t", str(duration_per_image), "-i", img]

    # Filter complex: fade geçişleri ile görselleri birleştir
    filter_parts = []
    for i in range(image_count):
        filter_parts.append(f"[{i}:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}]")

    concat_inputs = "".join([f"[v{i}]" for i in range(image_count)])
    filter_parts.append(f"{concat_inputs}concat=n={image_count}:v=1:a=0[outv]")

    filter_complex = ";".join(filter_parts)

    cmd = (
        input_args
        + ["-i", audio_path]
        + ["-filter_complex", filter_complex]
        + ["-map", "[outv]"]
        + ["-map", f"{image_count}:a"]
        + ["-c:v", "libx264", "-c:a", "aac"]
        + ["-shortest", "-y", output_path]
    )

    result = subprocess.run(
        ["ffmpeg"] + cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg hatası: {result.stderr[-500:]}")

    return output_path
