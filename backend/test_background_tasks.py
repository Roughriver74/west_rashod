"""Test script for background tasks system."""
import asyncio
import logging
from datetime import datetime, timedelta
from app.services.background_tasks import task_manager, TaskStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_simple_task(task_id: str):
    """Test simple background task."""
    logger.info(f"Starting test task {task_id}")

    # Simulate work with progress updates
    total = 100
    for i in range(total):
        await asyncio.sleep(0.05)  # Simulate work
        task_manager.update_progress(
            task_id,
            i + 1,
            message=f"Processing item {i + 1}/{total}"
        )

    return {"processed": total, "success": True}


async def test_failing_task(task_id: str):
    """Test failing task."""
    logger.info(f"Starting failing task {task_id}")

    for i in range(10):
        await asyncio.sleep(0.1)
        task_manager.update_progress(
            task_id,
            i + 1,
            message=f"Processing {i + 1}/10"
        )

    raise Exception("Simulated error for testing")


async def main():
    """Run tests."""
    print("=" * 60)
    print("Testing Background Tasks System")
    print("=" * 60)

    # Test 1: Simple successful task
    print("\n[TEST 1] Simple successful task")
    task_id_1 = task_manager.create_task(
        task_type="test_simple",
        total=100,
        metadata={"test": "simple"}
    )

    # Subscribe to updates
    def on_update(task_info):
        print(f"  → Progress: {task_info.progress}% - {task_info.message}")

    task_manager.subscribe(task_id_1, on_update)
    task_manager.run_async_task(task_id_1, test_simple_task)

    # Wait for completion
    await asyncio.sleep(6)

    task_1 = task_manager.get_task(task_id_1)
    assert task_1 is not None
    assert task_1.status == TaskStatus.COMPLETED
    assert task_1.progress == 100
    print(f"✓ Task completed: {task_1.result}")

    # Test 2: Failing task
    print("\n[TEST 2] Failing task")
    task_id_2 = task_manager.create_task(
        task_type="test_failing",
        total=10,
        metadata={"test": "failing"}
    )

    task_manager.run_async_task(task_id_2, test_failing_task)
    await asyncio.sleep(2)

    task_2 = task_manager.get_task(task_id_2)
    assert task_2 is not None
    assert task_2.status == TaskStatus.FAILED
    assert task_2.error is not None
    print(f"✓ Task failed as expected: {task_2.error}")

    # Test 3: Task cancellation
    print("\n[TEST 3] Task cancellation")
    task_id_3 = task_manager.create_task(
        task_type="test_cancel",
        total=100,
        metadata={"test": "cancel"}
    )

    task_manager.run_async_task(task_id_3, test_simple_task)
    await asyncio.sleep(0.5)  # Let it start

    cancelled = task_manager.cancel_task(task_id_3)
    assert cancelled is True
    await asyncio.sleep(0.5)

    task_3 = task_manager.get_task(task_id_3)
    assert task_3 is not None
    assert task_3.status == TaskStatus.CANCELLED
    print(f"✓ Task cancelled successfully")

    # Test 4: List all tasks
    print("\n[TEST 4] List all tasks")
    all_tasks = task_manager.get_all_tasks()
    print(f"✓ Total tasks: {len(all_tasks)}")
    for task in all_tasks:
        print(f"  - {task.task_id[:8]}... [{task.status.value}] {task.task_type}")

    # Test 5: Cleanup old tasks
    print("\n[TEST 5] Cleanup (no old tasks yet)")
    removed = task_manager.cleanup_old_tasks(max_age_hours=0)
    print(f"✓ Would remove {len([t for t in all_tasks if t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]])} completed tasks")

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
