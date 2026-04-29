from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.models.job import SessionLocal, Job, init_db
from app.workers.tasks import start_pipeline
import uuid
import asyncio
import json

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

        start_pipeline(
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

@router.get("/jobs", response_model=list[JobResponse])
def list_jobs():
    db = SessionLocal()
    try:
        jobs = db.query(Job).order_by(Job.created_at.desc()).all()
        return [
            JobResponse(
                id=job.id,
                topic=job.topic,
                language=job.language,
                status=job.status,
                current_step=job.current_step,
                result_text=job.result_text,
                error_msg=job.error_msg,
            )
            for job in jobs
        ]
    finally:
        db.close()


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    async def event_generator():
        while True:
            db = SessionLocal()
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if not job:
                    break
                data = json.dumps({
                    "status": job.status,
                    "current_step": job.current_step,
                    "error_msg": job.error_msg,
                })
                yield f"data: {data}\n\n"
                if job.status in ("completed", "failed"):
                    break
            finally:
                db.close()
            await asyncio.sleep(2)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/jobs/{job_id}/files")
def get_job_files(job_id: str):
    import os
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/app/outputs")
    job_dir = os.path.join(OUTPUT_DIR, job_id)

    if not os.path.exists(job_dir):
        raise HTTPException(status_code=404, detail="Job files not found")

    files = {}

    audio_path = os.path.join(job_dir, "audio.mp3")
    if os.path.exists(audio_path):
        files["audio"] = f"/api/jobs/{job_id}/download/audio"

    images_dir = os.path.join(job_dir, "images")
    if os.path.exists(images_dir):
        image_files = sorted([
            f for f in os.listdir(images_dir)
            if f.endswith(".png")
        ])
        files["images"] = [
            f"/api/jobs/{job_id}/download/images/{f}"
            for f in image_files
        ]

    video_path = os.path.join(job_dir, "video.mp4")
    if os.path.exists(video_path):
        files["video"] = f"/api/jobs/{job_id}/download/video"

    return files


@router.get("/jobs/{job_id}/download/{file_type}")
def download_file(job_id: str, file_type: str):
    from fastapi.responses import FileResponse
    import os
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/app/outputs")

    if file_type == "audio":
        path = os.path.join(OUTPUT_DIR, job_id, "audio.mp3")
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Audio not found")
        return FileResponse(path, media_type="audio/mpeg", filename="audio.mp3")

    if file_type == "video":
        path = os.path.join(OUTPUT_DIR, job_id, "video.mp4")
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Video not found")
        return FileResponse(path, media_type="video/mp4", filename="video.mp4")

    raise HTTPException(status_code=400, detail="Invalid file type")


@router.get("/jobs/{job_id}/download/images/{filename}")
def download_image(job_id: str, filename: str):
    from fastapi.responses import FileResponse
    import os
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/app/outputs")

    path = os.path.join(OUTPUT_DIR, job_id, "images", filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type="image/png", filename=filename)