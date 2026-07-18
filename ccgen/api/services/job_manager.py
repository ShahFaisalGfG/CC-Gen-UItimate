# job_manager.py — in-memory job registry; runs Pipeline.run() off the event loop
#
# Direct async translation of the previous QRunnable-based TranscriptionWorker: prepare(),
# check cancellation, run(progress_cb, segment_cb), emit a finished event. Callbacks execute on
# a worker thread (via run_in_executor), so events are handed back to the loop thread with
# call_soon_threadsafe before being placed on the per-job asyncio.Queue.

import asyncio
import logging
import uuid
from typing import Any, AsyncIterator, Optional

from ccgen.core import Segment
from ccgen.core.pipeline import Pipeline, PipelineConfig, PipelineResult

_log = logging.getLogger(__name__)


class JobManager:
    """Tracks running pipeline jobs and fans out progress events to stream subscribers."""

    def __init__(self) -> None:
        self._pipelines: dict[str, Pipeline] = {}
        self._queues: dict[str, "asyncio.Queue[dict[str, Any]]"] = {}
        self._results: dict[str, PipelineResult] = {}
        self._cancelled: set[str] = set()

    async def start_job(self, config: PipelineConfig) -> str:
        """Create a job id, launch its pipeline as a background task, and return the id.

        Must be called from a coroutine running on the event loop (an async route handler),
        since it schedules the job via asyncio.create_task().
        """
        job_id = uuid.uuid4().hex
        queue: "asyncio.Queue[dict[str, Any]]" = asyncio.Queue()
        self._queues[job_id] = queue
        pipeline = Pipeline(config)
        self._pipelines[job_id] = pipeline
        asyncio.create_task(self._run_job(job_id, pipeline, queue))
        return job_id

    def cancel_job(self, job_id: str) -> bool:
        """Request cancellation of a running job. Returns False when the job is unknown."""
        if job_id not in self._pipelines:
            return False
        self._cancelled.add(job_id)
        return True

    def get_result(self, job_id: str) -> Optional[PipelineResult]:
        """Return the completed result for a job, or None while it is still running."""
        return self._results.get(job_id)

    def is_known(self, job_id: str) -> bool:
        """Return True when the job id was issued by this manager."""
        return job_id in self._pipelines

    async def stream(self, job_id: str) -> AsyncIterator[dict[str, Any]]:
        """Yield queued event dicts for a job until its "finished" event arrives."""
        queue = self._queues.get(job_id)
        if queue is None:
            return
        while True:
            event = await queue.get()
            yield event
            if event.get("event") == "finished":
                break

    async def _run_job(
        self,
        job_id: str,
        pipeline: Pipeline,
        queue: "asyncio.Queue[dict[str, Any]]",
    ) -> None:
        """Run pipeline.prepare()+run() in a worker thread, forwarding events into the queue."""
        loop = asyncio.get_running_loop()

        def emit(event: dict[str, Any]) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, event)

        def status_cb(message: str) -> None:
            emit({"event": "status", "message": message})

        def segment_cb(seg: Segment) -> None:
            emit({
                "event": "segment",
                "id": seg["id"], "start": seg["start"], "end": seg["end"], "text": seg["text"],
            })

        def progress_num_cb(done: int, total: int) -> None:
            emit({"event": "progress", "done": done, "total": total})

        try:
            await loop.run_in_executor(None, pipeline.prepare, status_cb, progress_num_cb)
            if job_id in self._cancelled:
                emit({
                    "event": "finished", "success": False,
                    "error": "Cancelled by user.", "output_files": [],
                })
                return
            result = await loop.run_in_executor(
                None, lambda: pipeline.run(status_cb, segment_cb, progress_num_cb)
            )
            self._results[job_id] = result
            emit({
                "event": "finished",
                "success": result.success,
                "error": result.error,
                "output_files": result.output_files,
            })
        except Exception as e:
            _log.error("Job %s failed: %r", job_id, e, exc_info=True)
            emit({"event": "finished", "success": False, "error": str(e), "output_files": []})
        finally:
            self._cancelled.discard(job_id)
