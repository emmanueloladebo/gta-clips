import asyncio
from workers.candidate_worker import GroqCandidateWorker

async def test():
    worker = GroqCandidateWorker()
    boring_transcript = (
        "Yeah so I was just eating breakfast today and then I walked over to the computer. "
        "I'm driving down the highway right now, the weather is nice in Vice City. "
        "Just going to the ammunition shop to buy some ammo. Nothing much going on right now."
    )
    results = await worker.score_transcript(boring_transcript, 45.0)
    print(f"\nBoring transcript returned {len(results)} highlights (Should be 0 if strict):")
    for h in results:
        print(f"Hook: {h.hook_summary}, Score: {h.score}")

if __name__ == "__main__":
    asyncio.run(test())
