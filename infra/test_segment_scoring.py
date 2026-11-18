import asyncio
from packages.shared.database import AsyncSessionLocal
from packages.shared.models import Transcript
from workers.candidate_worker import GroqCandidateWorker
from sqlalchemy import select

async def main():
    worker = GroqCandidateWorker()
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Transcript).order_by(Transcript.id.desc()).limit(3))
        transcripts = res.scalars().all()
        for t in transcripts:
            print(f"\n--- Testing Transcript ID {t.id} (Segment {t.segment_id}) ---")
            print(f"Full text: '{t.text}'")
            highlights = await worker.score_transcript(t.text, 60.0)
            print(f"Groq highlights returned: {len(highlights)}")
            for h in highlights:
                print(f"  Score: {h.score}, Headline: {h.headline}, Hook: {h.hook_summary}")

if __name__ == "__main__":
    asyncio.run(main())
