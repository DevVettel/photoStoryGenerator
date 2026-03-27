from celery import Celery
from app.services.llm import generate_story
from app.models.job import SessionLocal, Job
import os
import tempfile

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("photostory", broker=REDIS_URL, backend=REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Istanbul",
)


@celery_app.task(bind=True, name="generate_story_task")
def generate_story_task(self, job_id: str, topic: str, language: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        job.status = "running"
        job.current_step = "text"
        db.commit()

        story = generate_story(topic=topic, language=language)

        job.status = "completed"
        job.current_step = None
        job.result_text = story
        db.commit()

        return {"job_id": job_id, "status": "completed"}

    except Exception as e:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_msg = str(e)
            db.commit()
        raise self.retry(exc=e, countdown=5, max_retries=2)
    finally:
        db.close()
