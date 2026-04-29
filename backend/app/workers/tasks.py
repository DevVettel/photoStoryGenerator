from celery import Celery, chain
from app.services.llm import generate_story
from app.services.tts import generate_audio
from app.services.image import generate_images
from app.services.video import assemble_video
from app.models.job import SessionLocal, Job
import os
import uuid

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("photostory", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Istanbul",
)

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/tmp/photostory")


def _get_job(db, job_id):
    return db.query(Job).filter(Job.id == job_id).first()


def _update_job(db, job_id, **kwargs):
    job = _get_job(db, job_id)
    if job:
        for k, v in kwargs.items():
            setattr(job, k, v)
        db.commit()


@celery_app.task(bind=True, name="generate_story_task")
def generate_story_task(self, job_id: str, topic: str, language: str):
    db = SessionLocal()
    try:
        _update_job(db, job_id, status="running", current_step="text")

        story = generate_story(topic=topic, language=language)

        _update_job(db, job_id, result_text=story)

        return {"job_id": job_id, "story": story, "topic": topic}

    except Exception as e:
        _update_job(db, job_id, status="failed", error_msg=str(e))
        raise self.retry(exc=e, countdown=5, max_retries=2)
    finally:
        db.close()


@celery_app.task(bind=True, name="generate_audio_task")
def generate_audio_task(self, prev_result: dict):
    job_id = prev_result["job_id"]
    story = prev_result["story"]
    topic = prev_result["topic"]

    db = SessionLocal()
    try:
        _update_job(db, job_id, current_step="audio")

        job_dir = os.path.join(OUTPUT_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)
        audio_path = os.path.join(job_dir, "audio.mp3")

        generate_audio(text=story, output_path=audio_path)

        return {
            "job_id": job_id,
            "story": story,
            "topic": topic,
            "audio_path": audio_path,
        }

    except Exception as e:
        _update_job(db, job_id, status="failed", error_msg=str(e))
        raise self.retry(exc=e, countdown=5, max_retries=2)
    finally:
        db.close()


@celery_app.task(bind=True, name="generate_images_task")
def generate_images_task(self, prev_result: dict):
    job_id = prev_result["job_id"]
    story = prev_result["story"]
    topic = prev_result["topic"]
    audio_path = prev_result["audio_path"]

    db = SessionLocal()
    try:
        _update_job(db, job_id, current_step="images")

        job_dir = os.path.join(OUTPUT_DIR, job_id)
        images_dir = os.path.join(job_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        image_paths = generate_images(
            story_text=story,
            topic=topic,
            output_dir=images_dir,
            count=3,
        )

        return {
            "job_id": job_id,
            "audio_path": audio_path,
            "image_paths": image_paths,
        }

    except Exception as e:
        _update_job(db, job_id, status="failed", error_msg=str(e))
        raise self.retry(exc=e, countdown=5, max_retries=2)
    finally:
        db.close()


@celery_app.task(bind=True, name="assemble_video_task")
def assemble_video_task(self, prev_result: dict):
    job_id = prev_result["job_id"]
    audio_path = prev_result["audio_path"]
    image_paths = prev_result["image_paths"]

    db = SessionLocal()
    try:
        _update_job(db, job_id, current_step="video")

        job_dir = os.path.join(OUTPUT_DIR, job_id)
        output_path = os.path.join(job_dir, "video.mp4")

        assemble_video(
            audio_path=audio_path,
            image_paths=image_paths,
            output_path=output_path,
        )

        _update_job(db, job_id, status="completed", current_step=None)

        return {
            "job_id": job_id,
            "video_path": output_path,
        }

    except Exception as e:
        _update_job(db, job_id, status="failed", error_msg=str(e))
        raise self.retry(exc=e, countdown=5, max_retries=2)
    finally:
        db.close()


def start_pipeline(job_id: str, topic: str, language: str):
    pipeline = chain(
        generate_story_task.s(job_id=job_id, topic=topic, language=language),
        generate_audio_task.s(),
        generate_images_task.s(),
        assemble_video_task.s(),
    )
    pipeline.delay()
