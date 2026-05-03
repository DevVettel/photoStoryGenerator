"""
Sadece video assembly adımını test eder.
Mevcut bir job'ın ses ve görsellerini kullanır — API çağrısı yapmaz.
Kullanım: python test_video.py <job_id>
"""
import sys
import os

# Ortam değişkenlerini yükle
from dotenv import load_dotenv
load_dotenv(".env")

# OUTPUT_DIR'i ayarla
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/app/outputs")

def test_video_assembly(job_id: str):
    from app.services.video import assemble_video

    job_dir = os.path.join(OUTPUT_DIR, job_id)
    audio_path = os.path.join(job_dir, "audio.mp3")
    images_dir = os.path.join(job_dir, "images")
    output_path = os.path.join(job_dir, "video_test.mp4")

    # Dosyaları kontrol et
    if not os.path.exists(audio_path):
        print(f"HATA: Ses dosyası bulunamadı: {audio_path}")
        sys.exit(1)

    image_paths = sorted([
        os.path.join(images_dir, f)
        for f in os.listdir(images_dir)
        if f.endswith(".png")
    ])

    if not image_paths:
        print(f"HATA: Görsel bulunamadı: {images_dir}")
        sys.exit(1)

    print(f"Ses: {audio_path}")
    print(f"Görseller: {image_paths}")
    print(f"Çıktı: {output_path}")
    print("FFmpeg çalışıyor...")

    result = assemble_video(
        audio_path=audio_path,
        image_paths=image_paths,
        output_path=output_path,
    )

    size = os.path.getsize(result) / (1024 * 1024)
    print(f"Başarılı! Video: {result} ({size:.2f} MB)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Argüman verilmezse son job'ı bul
        outputs = sorted(os.listdir(OUTPUT_DIR))
        if not outputs:
            print("HATA: Hiç job yok.")
            sys.exit(1)
        job_id = outputs[-1]
        print(f"Son job kullanılıyor: {job_id}")
    else:
        job_id = sys.argv[1]

    test_video_assembly(job_id)
