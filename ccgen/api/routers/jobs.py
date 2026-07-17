# jobs.py — routes to start, poll, cancel, and stream transcription/translation jobs

import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from ccgen.api.schemas.job import JobConfig
from ccgen.api.services.job_manager import JobManager
from ccgen.core.pipeline import PipelineConfig

_log = logging.getLogger(__name__)
router = APIRouter()
_manager = JobManager()


@router.post("/jobs")
async def start_job(config: JobConfig) -> dict[str, str]:
    """Start a new transcription/translation/transliteration job."""
    try:
        pipeline_config = PipelineConfig(**config.model_dump())
        job_id = await _manager.start_job(pipeline_config)
        return {"job_id": job_id}
    except Exception as e:
        _log.error("Failed to start job: %r", e, exc_info=True)
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    """Return the current status/result snapshot for a job."""
    if not _manager.is_known(job_id):
        raise HTTPException(status_code=404, detail="Unknown job id")
    result = _manager.get_result(job_id)
    if result is None:
        return {"job_id": job_id, "busy": True}
    return {
        "job_id": job_id,
        "busy": False,
        "success": result.success,
        "error": result.error,
        "output_files": result.output_files,
    }


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> dict[str, bool]:
    """Request cancellation of a running job."""
    if not _manager.cancel_job(job_id):
        raise HTTPException(status_code=404, detail="Unknown job id")
    return {"cancelled": True}


@router.websocket("/jobs/{job_id}/stream")
async def stream_job(websocket: WebSocket, job_id: str) -> None:
    """Stream live segment/progress/status/finished events for a job."""
    await websocket.accept()
    try:
        async for event in _manager.stream(job_id):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        _log.debug("Client disconnected from job %s stream", job_id)
