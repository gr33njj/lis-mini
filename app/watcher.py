"""File watcher module for monitoring NAS."""
import os
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import FileRecord, AuditLog, SessionLocal
from config import settings


def calculate_sha256(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


async def log_audit(
    db: AsyncSession,
    record_id: Optional[int],
    action: str,
    status: str,
    message: str,
    details: Optional[str] = None
):
    """Log audit entry."""
    log = AuditLog(
        record_id=record_id,
        action=action,
        status=status,
        message=message,
        details=details
    )
    db.add(log)
    await db.commit()


async def process_new_file(file_path: Path, db: AsyncSession) -> Optional[FileRecord]:
    """Process a new PDF file."""
    try:
        # Extract order number from filename
        order_no = file_path.stem
        
        # Calculate hash
        file_hash = calculate_sha256(str(file_path))
        
        # Check if file already processed (by hash)
        result = await db.execute(
            select(FileRecord).where(FileRecord.file_hash == file_hash)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            await log_audit(
                db, existing.id, "file_detected", "info",
                f"File {file_path.name} already processed (duplicate hash)"
            )
            return None
        
        # Create new record
        record = FileRecord(
            order_no=order_no,
            file_name=file_path.name,
            file_hash=file_hash,
            file_path=str(file_path),
            status="pending"
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        
        await log_audit(
            db, record.id, "file_detected", "success",
            f"New file detected: {file_path.name}, Order: {order_no}"
        )
        
        print(f"[Watcher] New file detected: {file_path.name} (Order: {order_no})")
        return record
        
    except Exception as e:
        await log_audit(
            db, None, "file_detected", "error",
            f"Error processing file {file_path.name}: {str(e)}"
        )
        print(f"[Watcher] Error processing {file_path.name}: {e}")
        return None


async def watch_directory():
    """Watch NAS directory for new files."""
    watch_path = Path(settings.NAS_WATCH_PATH)
    
    # Create directory if not exists
    watch_path.mkdir(parents=True, exist_ok=True)
    
    print(f"[Watcher] Started watching: {watch_path}")
    
    # Track processed files
    processed_files = set()
    
    while True:
        try:
            async with SessionLocal() as db:
                # Scan for PDF files
                for file_path in watch_path.glob("*.pdf"):
                    if file_path.name not in processed_files:
                        record = await process_new_file(file_path, db)
                        if record:
                            processed_files.add(file_path.name)
                
            await asyncio.sleep(settings.WATCH_INTERVAL)
            
        except Exception as e:
            print(f"[Watcher] Error in watch loop: {e}")
            await asyncio.sleep(settings.WATCH_INTERVAL)


async def start_watcher():
    """Start the file watcher."""
    asyncio.create_task(watch_directory())

