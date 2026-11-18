import asyncio
from packages.shared.database import AsyncSessionLocal
from packages.shared.models import Candidate, Transcript, Clip
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Transcript).order_by(Transcript.id.desc()).limit(5))
        transcripts = res.scalars().all()
        print(f"Total recent transcripts: {len(transcripts)}")
        for t in transcripts:
            print(f"Transcript ID {t.id} (Segment {t.segment_id}): {t.text[:120]}...")

        cres = await db.execute(select(Candidate).order_by(Candidate.id.desc()).limit(5))
        candidates = cres.scalars().all()
        print(f"\nTotal recent candidates: {len(candidates)}")
        for c in candidates:
            print(f"Candidate ID {c.id}: score={c.score}, headline='{c.headline}', hook='{c.hook_summary}', quote='{c.evidence_quote}'")

        clip_res = await db.execute(select(Clip).order_by(Clip.id.desc()).limit(5))
        clips = clip_res.scalars().all()
        print(f"\nTotal recent clips: {len(clips)}")
        for cl in clips:
            print(f"Clip ID {cl.id}: title='{cl.title}', status='{cl.approval_status}', r2_key='{cl.r2_key}'")

if __name__ == "__main__":
    asyncio.run(main())
