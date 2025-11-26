"""1C Integration module with Telegram notifications."""
import asyncio
import base64
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import FileRecord, AuditLog, SessionLocal
from config import settings
from watcher import log_audit
from pdf_parser import parse_lab_result_pdf
from integrator_1c import get_1c_integrator
from telegram_notifier import notify_success, notify_error


async def send_to_1c(
    record: FileRecord,
    db: AsyncSession,
    retry_count: int = 0
) -> bool:
    """
    Parse PDF and send data to 1C via HTTP API.
    Uses new PDF parser and 1C integrator.
    Sends Telegram notifications on success/error.
    """
    patient_name = ""
    try:
        # Check file exists
        file_path = Path(record.file_path)
        if not file_path.exists():
            error_msg = f"File not found: {record.file_path}"
            await log_audit(
                db, record.id, "send_to_1c", "error", error_msg
            )
            # Отправляем уведомление об ошибке
            await notify_error(
                patient_name="Неизвестно",
                error_text=error_msg
            )
            return False
        
        print(f"[Integrator] Processing {record.file_name}...")
        
        # Step 1: Parse PDF
        loop = asyncio.get_event_loop()
        parsed_data = await loop.run_in_executor(
            None, 
            parse_lab_result_pdf, 
            str(file_path)
        )
        
        patient_name = parsed_data.get('patient_name', 'N/A')
        print(f"[Integrator] ✓ Parsed PDF: {patient_name}")
        
        # Step 2: Send to 1C
        integrator = get_1c_integrator()
        
        # Выбираем метод интеграции (createAppointment или fillTemplate)
        integration_mode = os.getenv("C1_INTEGRATION_MODE", "createAppointment")
        
        if integration_mode == "createAppointment":
            result = await loop.run_in_executor(
                None,
                integrator.create_appointment,
                parsed_data
            )
        else:
            result = await loop.run_in_executor(
                None,
                integrator.fill_template,
                parsed_data
            )
        
        if result.get("success"):
            # Update record
            record.sent_to_1c = True
            record.sent_to_1c_at = datetime.utcnow()
            record.patient_email = parsed_data.get("patient_email", "")
            record.status = "completed"
            
            # Save parsed data to record for future reference
            import json
            record.error_message = json.dumps(parsed_data, ensure_ascii=False)[:500]
            
            await db.commit()
            
            await log_audit(
                db, record.id, "send_to_1c", "success",
                f"Successfully sent to 1C. Patient: {patient_name}",
                details=str(result)
            )
            
            print(f"[Integrator] ✓ Sent to 1C: {record.file_name}")
            
            # ⭐ НОВОЕ: Отправляем Telegram уведомление об успехе
            document_number = result.get("appointment_number", "???")
            template_name = result.get("template", "")
            parameters_count = result.get("parameters_filled", 0)
            
            await notify_success(
                patient_name=patient_name,
                document_number=document_number,
                template_name=template_name,
                parameters_count=parameters_count
            )
            
            # Archive file
            await archive_file(record, db)
            
            return True
        else:
            error_response = result.get("error", "Unknown error")
            raise Exception(f"1C returned error: {error_response}")
            
    except Exception as e:
        error_msg = str(e)
        record.error_message = error_msg
        record.retry_count = retry_count + 1
        
        await log_audit(
            db, record.id, "send_to_1c", "error",
            f"Failed to send to 1C (attempt {retry_count + 1}): {error_msg}"
        )
        
        print(f"[Integrator] ✗ Error: {error_msg}")
        
        # Retry logic
        if retry_count < settings.API_1C_RETRY_COUNT:
            print(f"[Integrator] Retry {retry_count + 1} for {record.file_name}")
            await asyncio.sleep(settings.API_1C_RETRY_DELAY * (retry_count + 1))
            return await send_to_1c(record, db, retry_count + 1)
        else:
            # Move to quarantine
            record.status = "failed"
            await db.commit()
            await move_to_quarantine(record, db)
            
            # ⭐ НОВОЕ: Отправляем Telegram уведомление об ошибке
            await notify_error(
                patient_name=patient_name if patient_name else "Неизвестно",
                error_text=error_msg
            )
            
            print(f"[Integrator] ✗ Failed after {settings.API_1C_RETRY_COUNT} attempts: {record.file_name}")
            return False


async def archive_file(record: FileRecord, db: AsyncSession):
    """Archive processed file."""
    try:
        source = Path(record.file_path)
        if not source.exists():
            return
        
        # Create archive directory (YYYY-MM-DD)
        date_str = datetime.now().strftime("%Y-%m-%d")
        archive_dir = Path(settings.NAS_ARCHIVE_PATH) / date_str
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Move file
        destination = archive_dir / record.file_name
        source.rename(destination)
        
        record.archived_at = datetime.utcnow()
        await db.commit()
        
        await log_audit(
            db, record.id, "archive", "success",
            f"File archived to {destination}"
        )
        
        print(f"[Integrator] Archived: {record.file_name}")
        
    except Exception as e:
        await log_audit(
            db, record.id, "archive", "error",
            f"Failed to archive: {str(e)}"
        )


async def move_to_quarantine(record: FileRecord, db: AsyncSession):
    """Move failed file to quarantine."""
    try:
        source = Path(record.file_path)
        if not source.exists():
            return
        
        # Create quarantine directory
        quarantine_dir = Path(settings.NAS_QUARANTINE_PATH)
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        
        # Move file
        destination = quarantine_dir / record.file_name
        source.rename(destination)
        
        # Save error log
        error_log = destination.with_suffix('.error.txt')
        with open(error_log, 'w') as f:
            f.write(f"Order: {record.order_no}\n")
            f.write(f"Error: {record.error_message}\n")
            f.write(f"Attempts: {record.retry_count}\n")
            f.write(f"Date: {datetime.now()}\n")
        
        await log_audit(
            db, record.id, "quarantine", "success",
            f"File moved to quarantine: {destination}"
        )
        
        print(f"[Integrator] Quarantined: {record.file_name}")
        
    except Exception as e:
        await log_audit(
            db, record.id, "quarantine", "error",
            f"Failed to move to quarantine: {str(e)}"
        )


async def process_queue():
    """Process pending files queue."""
    print("[Integrator] Started processing queue")
    
    while True:
        try:
            async with SessionLocal() as db:
                # Get pending records
                result = await db.execute(
                    select(FileRecord)
                    .where(FileRecord.status == "pending")
                    .where(FileRecord.sent_to_1c == False)
                    .order_by(FileRecord.created_at)
                )
                pending_records = result.scalars().all()
                
                count = len(pending_records)
                if count > 0:
                    print(f"[Integrator] Found {count} pending file(s)")
                
                for record in pending_records:
                    print(f"[Integrator] Processing file: {record.file_name} (id={record.id})")
                    record.status = "processing"
                    await db.commit()
                    
                    try:
                        success = await send_to_1c(record, db)
                        print(f"[Integrator] File {record.file_name}: {'SUCCESS' if success else 'FAILED'}")
                    except Exception as e:
                        print(f"[Integrator] EXCEPTION processing {record.file_name}: {e}")
                        import traceback
                        traceback.print_exc()
            
            await asyncio.sleep(5)  # Check queue every 5 seconds
            
        except Exception as e:
            print(f"[Integrator] Error in queue processing: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(10)


async def start_integrator():
    """Start the integrator."""
    task = asyncio.create_task(process_queue())
    return task
