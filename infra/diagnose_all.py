import asyncio
from packages.shared.database import AsyncSessionLocal
from packages.shared.models import Streamer, StreamSession, Segment, Transcript, Candidate, Clip
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        # Streamers
        s_res = await db.execute(select(Streamer))
        streamers = s_res.scalars().all()
        print(f"=== STREAMERS ({len(streamers)}) ===")
        for s in streamers:
            print(f"ID {s.id}: {s.display_name} ({s.platform}) - status={s.live_status}, viewers={s.viewer_count}, title='{s.stream_title}'")

        # Sessions
        sess_res = await db.execute(select(StreamSession).order_by(StreamSession.id.desc()).limit(5))
        sessions = sess_res.scalars().all()
        print(f"\n=== RECENT SESSIONS ({len(sessions)}) ===")
        for ss in sessions:
            print(f"Session {ss.id}: Streamer {ss.streamer_id}, status={ss.status}, started={ss.started_at}")

        # Segments
        seg_res = await db.execute(select(Segment).order_by(Segment.id.desc()).limit(10))
        segments = seg_res.scalars().all()
        print(f"\n=== RECENT SEGMENTS ({len(segments)}) ===")
        for seg in segments:
            print(f"Segment {seg.id}: session={seg.session_id}, status={seg.status}, duration={seg.duration_seconds}s, size={seg.disk_bytes} bytes, file={seg.file_path}")

        # Transcripts
        t_res = await db.execute(select(Transcript).order_by(Transcript.id.desc()).limit(5))
        transcripts = t_res.scalars().all()
        print(f"\n=== RECENT TRANSCRIPTS ({len(transcripts)}) ===")
        for t in transcripts:
            print(f"Transcript for Segment {t.segment_id}: '{t.text[:120]}...'")

        # Candidates
        c_res = await db.execute(select(Candidate).order_by(Candidate.id.desc()).limit(5))
        candidates = c_res.scalars().all()
        print(f"\n=== RECENT CANDIDATES ({len(candidates)}) ===")
        for c in candidates:
            print(f"Candidate {c.id}: seg={c.segment_id}, score={c.score}, hook='{c.hook_summary}', status={c.status}")

        # Clips
        clip_res = await db.execute(select(Clip).order_by(Clip.id.desc()).limit(5))
        clips = clip_res.scalars().all()
        print(f"\n=== RECENT CLIPS ({len(clips)}) ===")
        for cl in clips:
            print(f"Clip {cl.id}: title='{cl.title}', status='{cl.approval_status}'")

if __name__ == "__main__":
    asyncio.run(main())
