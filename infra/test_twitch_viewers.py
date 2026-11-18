import asyncio
from packages.shared.database import AsyncSessionLocal
from packages.shared.models import Streamer
from packages.shared.platforms import check_streamer_live
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Streamer))
        streamers = res.scalars().all()
        for s in streamers:
            info = await check_streamer_live(s.platform, s.channel_id, s.channel_url)
            print(f"Streamer {s.display_name} (@{s.channel_id}): is_live={info['is_live']}, live_viewers={info.get('viewers')}, db_viewers={s.viewer_count}")

if __name__ == "__main__":
    asyncio.run(main())
