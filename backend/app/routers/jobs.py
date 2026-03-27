from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.job import SessionLocal, Job, init_db
from app.workers.tasks import generate_story_task
import uuid

router = APIRouter()
init_db()


class JobCreate(BaseModel):
    topic: str
    language: str = "tr"


class JobResponse(BaseModel):
    id: str
    topic: str
    language: str
    status: str
    current_step: str | None
    result_text: str | None
    error_msg: str | None


@router.post("/jobs", response_model=JobResponse, status_code=201)
def create_job(payload: JobCreate):
    db = SessionLocal()
    try:
        job = Job(
            id=str(uuid.uuid4()),
            topic=payload.topic,
            language=payload.language,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        generate_story_task.delay(
            job_id=job.id,
            topic=job.topic,
            language=job.language,
        )

        return JobResponse(
            id=job.id,
            topic=job.topic,
            language=job.language,
            status=job.status,
            current_step=job.current_step,
            result_text=job.result_text,
            error_msg=job.error_msg,
        )
    finally:
        db.close()


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return JobResponse(
            id=job.id,
            topic=job.topic,
            language=job.language,
            status=job.status,
            current_step=job.current_step,
            result_text=job.result_text,
            error_msg=job.error_msg,
        )
    finally:
        db.close()
