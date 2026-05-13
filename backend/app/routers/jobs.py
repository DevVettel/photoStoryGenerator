from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.models.job import SessionLocal, Job, init_db
from app.workers.tasks import start_pipeline
import uuid
import asyncio
import json
import os
import re

router = APIRouter()
init_db()

AUDIO_FILE = "audio.mp3"
VIDEO_FILE = "video.mp4"

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
)
_SAFE_FILENAME_RE = re.compile(r'^[a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+$')


def _get_output_dir() -> str:
    return os.getenv("OUTPUT_DIR", "/app/outputs")


def _safe_job_dir(job_id: str) -> str:
    if not _UUID_RE.match(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    output_dir = _get_output_dir()
    resolved_base = os.path.realpath(output_dir)
    job_dir = os.path.realpath(os.path.join(output_dir, job_id))
    if not job_dir.startswith(resolved_base + os.sep):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    return job_dir


class JobCreate(BaseModel):
    topic: str
    language: str = "tr"
    skip_images: bool = False


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
            skip_images=str(payload.skip_images).lower(),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        start_pipeline(
            job_id=job.id,
            topic=job.topic,
            language=job.language,
            skip_images=payload.skip_images,
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


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    responses={404: {"description": "Job not found"}},
)
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


@router.get(
    "/jobs/{job_id}/files",
    responses={404: {"description": "Job files not found"}},
)
def get_job_files(job_id: str):
    job_dir = _safe_job_dir(job_id)

    if not os.path.exists(job_dir):
        raise HTTPException(status_code=404, detail="Job files not found")

    files = {}

    audio_path = os.path.join(job_dir, AUDIO_FILE)
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

    video_path = os.path.join(job_dir, VIDEO_FILE)
    if os.path.exists(video_path):
        files["video"] = f"/api/jobs/{job_id}/download/video"

    return files


@router.get(
    "/jobs/{job_id}/download/{file_type}",
    responses={
        404: {"description": "File not found"},
        400: {"description": "Invalid file type"},
    },
)
def download_file(job_id: str, file_type: str):
    from fastapi.responses import FileResponse

    job_dir = _safe_job_dir(job_id)

    if file_type == "audio":
        path = os.path.join(job_dir, AUDIO_FILE)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Audio not found")
        return FileResponse(path, media_type="audio/mpeg", filename=AUDIO_FILE)

    if file_type == "video":
        path = os.path.join(job_dir, VIDEO_FILE)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Video not found")
        return FileResponse(path, media_type="video/mp4", filename=VIDEO_FILE)

    raise HTTPException(status_code=400, detail="Invalid file type")


@router.get(
    "/jobs/{job_id}/download/images/{filename}",
    responses={
        404: {"description": "Image not found"},
        400: {"description": "Invalid request"},
    },
)
def download_image(job_id: str, filename: str):
    from fastapi.responses import FileResponse

    job_dir = _safe_job_dir(job_id)

    if not _SAFE_FILENAME_RE.match(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    images_dir = os.path.join(job_dir, "images")
    resolved_images = os.path.realpath(images_dir)
    path = os.path.realpath(os.path.join(images_dir, filename))
    if not path.startswith(resolved_images + os.sep):
        raise HTTPException(status_code=400, detail="Invalid filename")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type="image/png", filename=filename)
