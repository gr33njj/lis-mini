"""Background maintenance tasks for the ЛИС МД system."""

import asyncio
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from config import settings


async def cleanup_archives() -> None:
    """Remove archived result directories older than the retention period."""
    archive_path = Path(settings.NAS_ARCHIVE_PATH)
    if not archive_path.exists():
        return

    retention_days = settings.ARCHIVE_RETENTION_DAYS
    cutoff_date = datetime.utcnow().date() - timedelta(days=retention_days)

    for entry in archive_path.iterdir():
        if not entry.is_dir():
            continue

        try:
            entry_date = datetime.strptime(entry.name, "%Y-%m-%d").date()
        except ValueError:
            # Skip directories that do not follow the YYYY-MM-DD naming convention
            continue

        if entry_date < cutoff_date:
            try:
                shutil.rmtree(entry)
                print(
                    f"[Housekeeping] Removed archive directory {entry} "
                    f"(older than {retention_days} days)"
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                print(f"[Housekeeping] Failed to remove {entry}: {exc}")


async def archive_housekeeping_loop() -> None:
    """Continuously perform archive cleanup once per day."""
    while True:
        try:
            await cleanup_archives()
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"[Housekeeping] Unexpected error during cleanup: {exc}")

        await asyncio.sleep(24 * 60 * 60)  # Run once every 24 hours


async def start_housekeeping() -> None:
    """Start housekeeping background tasks."""
    asyncio.create_task(archive_housekeeping_loop())

