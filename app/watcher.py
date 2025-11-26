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
    print(f"[Watcher] 🔧 process_new_file() called for: {file_path.name}", flush=True)
    try:
        # Extract order number from filename
        order_no = file_path.stem
        print(f"[Watcher]   order_no: {order_no}", flush=True)
        
        # Calculate hash
        print(f"[Watcher]   Calculating hash...", flush=True)
        file_hash = calculate_sha256(str(file_path))
        print(f"[Watcher]   hash: {file_hash[:16]}...", flush=True)
        
        # Check if file already processed (by hash)
        result = await db.execute(
            select(FileRecord).where(FileRecord.file_hash == file_hash)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"[Watcher]   ⚠️ File already processed (duplicate hash)", flush=True)
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
        
        print(f"[Watcher]   ✅ Record created, ID: {record.id}", flush=True)
        print(f"[Watcher] New file detected: {file_path.name} (Order: {order_no})", flush=True)
        return record
        
    except Exception as e:
        print(f"[Watcher]   ❌ EXCEPTION: {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        await log_audit(
            db, None, "file_detected", "error",
            f"Error processing file {file_path.name}: {str(e)}"
        )
        print(f"[Watcher] Error processing {file_path.name}: {e}", flush=True)
        return None


async def watch_directory():
    """Watch NAS directory for new files."""
    print("[Watcher] watch_directory() STARTED", flush=True)
    watch_path = Path(settings.NAS_WATCH_PATH)
    
    # Create directory if not exists
    watch_path.mkdir(parents=True, exist_ok=True)
    
    print(f"[Watcher] Started watching: {watch_path}", flush=True)
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Watcher started, watching: {watch_path}")
    
    # Track processed files by hash (not by name!)
    processed_hashes = set()
    
    while True:
        try:
            logger.info(f"[Watcher] Scanning directory, processed hashes: {len(processed_hashes)}")
            print(f"[Watcher] Scanning directory...", flush=True)
            
            async with SessionLocal() as db:
                # Scan for PDF files
                pdf_files = list(watch_path.glob("*.pdf"))
                logger.info(f"[Watcher] Found {len(pdf_files)} PDF files")
                print(f"[Watcher] Found {len(pdf_files)} PDF files", flush=True)
                
                for file_path in pdf_files:
                    # Calculate hash for quick check
                    try:
                        file_hash = calculate_sha256(str(file_path))
                    except Exception as e:
                        print(f"[Watcher] Error calculating hash for {file_path.name}: {e}", flush=True)
                        continue
                    
                    if file_hash not in processed_hashes:
                        print(f"[Watcher] Processing: {file_path.name}", flush=True)
                        record = await process_new_file(file_path, db)
                        if record:
                            processed_hashes.add(file_hash)
                            print(f"[Watcher] Added hash to processed: {file_path.name}", flush=True)
                        else:
                            # Даже если файл уже в базе, добавляем hash чтобы не проверять повторно
                            processed_hashes.add(file_hash)
                
            await asyncio.sleep(settings.WATCH_INTERVAL)
            
        except Exception as e:
            print(f"[Watcher] Error in watch loop: {e}")
            await asyncio.sleep(settings.WATCH_INTERVAL)


async def start_watcher():
    """Start the file watcher."""
    print("[Watcher] start_watcher() called", flush=True)
    task = asyncio.create_task(watch_directory())
    print(f"[Watcher] Task created: {task}", flush=True)
    return task

