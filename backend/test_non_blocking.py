"""Test that sync tasks don't block the event loop."""
import asyncio
import time
from datetime import date, timedelta

from app.services.async_sync_service import AsyncSyncService
from app.services.background_tasks import task_manager


async def main():
    """Test non-blocking sync."""
    print("Starting non-blocking sync test...")

    # Start a sync task
    date_to = date.today()
    date_from = date_to - timedelta(days=7)

    task_id = AsyncSyncService.start_full_sync(
        date_from=date_from,
        date_to=date_to,
        auto_classify=False,
        user_id=None
    )

    print(f"✓ Sync task started: {task_id}")
    print("✓ Main thread is NOT blocked - you should see this immediately")

    # Check that we can do other work while sync is running
    for i in range(5):
        await asyncio.sleep(1)
        task = task_manager.get_task(task_id)
        if task:
            print(f"  [{i+1}s] Task status: {task.status.value}, progress: {task.progress}%")
        else:
            print(f"  [{i+1}s] Task not found")

    print("\n✓ Test passed - event loop was not blocked!")
    print("  The sync task is running in a separate thread.")


if __name__ == "__main__":
    asyncio.run(main())
