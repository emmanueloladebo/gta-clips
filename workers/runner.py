"""
Unified Background Worker Orchestrator.
Runs all processing stages asynchronously in the cloud environment.
"""
import asyncio
import logging
import signal
import sys
from typing import NoReturn
from sqlalchemy import select

from packages.shared.config import settings
from packages.shared.database import init_db, AsyncSessionLocal
from packages.shared.models import Segment, Candidate, Clip
from packages.shared.enums import SegmentStatus, CandidateStatus, ApprovalStatus
from workers.capture_worker import capture_worker
from workers.transcription_worker import transcription_worker
from workers.candidate_worker import candidate_worker
from workers.render_worker import render_worker
from workers.storage_worker import storage_worker
from workers.cleanup_worker import cleanup_worker
from workers.publish_worker import publish_worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("worker_runner")

_shutdown_event = asyncio.Event()


def handle_signal(sig, frame):
    logger.info(f"Received signal {sig}, initiating graceful shutdown...")
    _shutdown_event.set()


async def capture_loop():
    while not _shutdown_event.is_set():
        try:
            await capture_worker.check_and_capture_streamers()
        except Exception as e:
            logger.error(f"Error in capture loop: {e}")
        await asyncio.sleep(30)


async def transcription_loop():
    while not _shutdown_event.is_set():
        try:
            async with AsyncSessionLocal() as db:
                stmt = select(Segment).where(Segment.status == SegmentStatus.RECORDED.value).limit(3)
                segments = (await db.execute(stmt)).scalars().all()

            for seg in segments:
                await transcription_worker.process_segment(seg.id)
        except Exception as e:
            logger.error(f"Error in transcription loop: {e}")
        await asyncio.sleep(10)


async def candidate_loop():
    while not _shutdown_event.is_set():
        try:
            async with AsyncSessionLocal() as db:
                stmt = select(Segment).where(Segment.status == SegmentStatus.TRANSCRIBED.value).limit(3)
                segments = (await db.execute(stmt)).scalars().all()

            for seg in segments:
                await candidate_worker.process_segment_candidates(seg.id)
        except Exception as e:
            logger.error(f"Error in candidate scoring loop: {e}")
        await asyncio.sleep(10)


async def render_loop():
    while not _shutdown_event.is_set():
        try:
            async with AsyncSessionLocal() as db:
                # Strictly render candidates that meet or exceed the viral threshold
                stmt = select(Candidate).where(
                    (Candidate.status == CandidateStatus.DETECTED.value) &
                    (Candidate.score >= settings.VIRAL_SCORE_THRESHOLD)
                ).limit(2)
                candidates = (await db.execute(stmt)).scalars().all()

            for cand in candidates:
                clip = await render_worker.render_candidate_to_clip(cand.id)
                if clip:
                    # Immediately upload to R2
                    await storage_worker.upload_clip_to_r2(clip.id)
        except Exception as e:
            logger.error(f"Error in render loop: {e}")
        await asyncio.sleep(10)


async def publish_loop():
    while not _shutdown_event.is_set():
        try:
            await publish_worker.evaluate_auto_post_queue()
            await publish_worker.process_queued_jobs()
        except Exception as e:
            logger.error(f"Error in publish loop: {e}")
        await asyncio.sleep(30)


async def cleanup_loop():
    while not _shutdown_event.is_set():
        try:
            logger.info("Executing 24-hour media retention sweep...")
            await cleanup_worker.execute_retention_sweep()
            await cleanup_worker.orphan_reconciliation()
        except Exception as e:
            logger.error(f"Error in cleanup loop: {e}")
        await asyncio.sleep(3600)  # Hourly sweep


async def main():
    logger.info("Starting GTA 6 Cloud Processing Workers...")
    await init_db()

    # Startup reconciliation: check stuck segments and run initial cleanup
    await capture_worker.startup_reconciliation()
    await cleanup_worker.execute_retention_sweep()
    await cleanup_worker.orphan_reconciliation()

    # Launch worker tasks
    tasks = [
        asyncio.create_task(capture_loop()),
        asyncio.create_task(transcription_loop()),
        asyncio.create_task(candidate_loop()),
        asyncio.create_task(render_loop()),
        asyncio.create_task(publish_loop()),
        asyncio.create_task(cleanup_loop()),
    ]

    try:
        await _shutdown_event.wait()
    finally:
        logger.info("Cancelling worker tasks...")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All workers stopped cleanly.")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    asyncio.run(main())
