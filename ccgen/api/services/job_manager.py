# job_manager.py - in-memory job registry; runs Pipeline.prepare()/run() off the event loop
#
# Callbacks execute on a worker thread (via run_in_executor), so events are handed back to the
# loop thread with call_soon_threadsafe before being placed on the per-job asyncio.Queue.
# Cancellation is cooperative: cancel_job() flags the pipeline, which stops at its next segment
# or download chunk and reports a cancelled result.

import asyncio
import logging
import uuid
from collections import OrderedDict
from typing import Any, AsyncIterator, Optional

from ccgen.core import AnySegment
from ccgen.core.pipeline import CANCELLED_MESSAGE, Pipeline, PipelineConfig, PipelineResult
from ccgen.engines import model_cache

_log = logging.getLogger(__name__)

# Finished results are kept for polling clients, but only the most recent ones, so a long
# session processing thousands of files doesn't grow memory without bound.
_MAX_KEPT_RESULTS = 100


class JobManager:
    """Tracks running pipeline jobs and fans out progress events to stream subscribers."""

    def __init__(self) -> None:
        self._pipelines: dict[str, Pipeline] = {}
        self._queues: dict[str, "asyncio.Queue[dict[str, Any]]"] = {}
        self._results: "OrderedDict[str, PipelineResult]" = OrderedDict()

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
        """Request cancellation of a job. Returns False when the job is unknown."""
        pipeline = self._pipelines.get(job_id)
        if pipeline is not None:
            pipeline.cancel()
            return True
        return job_id in self._results

    def get_result(self, job_id: str) -> Optional[PipelineResult]:
        """Return the completed result for a job, or None while it is still running."""
        return self._results.get(job_id)

    def is_known(self, job_id: str) -> bool:
        """Return True when the job id was issued by this manager."""
        return job_id in self._pipelines or job_id in self._results

    def release_models(self) -> bool:
        """Free every cached model unless a job is still running. Returns True when released."""
        if self._pipelines:
            return False
        model_cache.release_all()
        return True

    async def stream(self, job_id: str) -> AsyncIterator[dict[str, Any]]:
        """Yield queued event dicts for a job until its "finished" event arrives."""
        queue = self._queues.get(job_id)
        if queue is None:
            return
        try:
            while True:
                event = await queue.get()
                yield event
                if event.get("event") == "finished":
                    break
        finally:
            if job_id in self._results:
                self._queues.pop(job_id, None)

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

        def segment_cb(seg: AnySegment) -> None:
            if "transliterated" in seg:
                kind, text = "transliteration", seg["transliterated"]  # type: ignore[typeddict-item]
            elif "translated" in seg:
                kind, text = "translation", seg["translated"]  # type: ignore[typeddict-item]
            else:
                kind, text = "transcript", seg.get("text", "")
            emit({
                "event": "segment", "kind": kind,
                "id": seg["id"], "start": seg["start"], "end": seg["end"], "text": text,
            })

        def progress_num_cb(done: int, total: int) -> None:
            emit({"event": "progress", "done": done, "total": total})

        result: Optional[PipelineResult] = None
        try:
            await loop.run_in_executor(None, pipeline.prepare, status_cb, progress_num_cb)
            if pipeline.cancelled:
                result = _cancelled_result()
            else:
                result = await loop.run_in_executor(
                    None, lambda: pipeline.run(status_cb, segment_cb, progress_num_cb)
                )
        except Exception as e:
            if pipeline.cancelled:
                result = _cancelled_result()
            else:
                _log.error("Job %s failed: %r", job_id, e, exc_info=True)
                result = PipelineResult(success=False, input_path="", error=str(e) or repr(e))
        finally:
            result = result or _cancelled_result()
            self._store_result(job_id, result)
            # Dropping the pipeline releases its engines; models stay in the shared cache.
            self._pipelines.pop(job_id, None)
            emit({
                "event": "finished",
                "success": result.success,
                "error": result.error,
                "output_files": result.output_files,
            })

    def _store_result(self, job_id: str, result: PipelineResult) -> None:
        """Keep a compact copy of the result for polling, evicting the oldest ones."""
        self._results[job_id] = PipelineResult(
            success=result.success,
            input_path=result.input_path,
            output_files=result.output_files,
            detected_language=result.detected_language,
            error=result.error,
            cancelled=result.cancelled,
        )
        while len(self._results) > _MAX_KEPT_RESULTS:
            old_id, _ = self._results.popitem(last=False)
            self._queues.pop(old_id, None)


def _cancelled_result() -> PipelineResult:
    """Build the result reported for a job cancelled before or during its run."""
    return PipelineResult(success=False, input_path="", error=CANCELLED_MESSAGE, cancelled=True)
