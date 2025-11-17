"""Main FastAPI application."""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.security import HTTPBearer
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from database import init_db, get_db, FileRecord, AuditLog, User, SessionLocal
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, init_admin_user
)
from config import settings
from watcher import start_watcher
from integrator import start_integrator, send_to_1c
from mailer import send_email
from pdf_parser import parse_lab_result_pdf
from integrator_1c import get_1c_integrator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("🚀 Starting ЛИС МД...")
    
    # Initialize database
    await init_db()
    logger.info("✓ Database initialized")
    
    # Create database session
    app.state.db_session = SessionLocal
    
    # Create admin user
    async with app.state.db_session() as db:
        await init_admin_user(db)
    logger.info("✓ Admin user initialized")
    
    # Start background tasks
    await start_watcher()
    await start_integrator()
    logger.info("✓ Background services started")
    
    logger.info("✓ ЛИС МД started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ЛИС МД...")


app = FastAPI(
    title="ЛИС МД", 
    description="Система управления лабораторными результатами",
    lifespan=lifespan
)

# Setup templates
templates = Jinja2Templates(directory="templates")

# Exception handlers for unauthorized access
@app.exception_handler(401)
async def unauthorized_exception_handler(request: Request, exc: FastAPIHTTPException):
    """Redirect to login page for HTML requests when unauthorized."""
    # Check if this is a page request (not API)
    if not request.url.path.startswith("/api/"):
        return RedirectResponse(url="/login", status_code=302)
    # For API requests, return JSON error
    return JSONResponse(
        status_code=401,
        content={"detail": "Not authenticated"}
    )

@app.exception_handler(403)
async def forbidden_exception_handler(request: Request, exc: FastAPIHTTPException):
    """Redirect to login page for HTML requests when forbidden (no token)."""
    # Check if this is a page request (not API)
    if not request.url.path.startswith("/api/"):
        return RedirectResponse(url="/login", status_code=302)
    # For API requests, return JSON error
    return JSONResponse(
        status_code=403,
        content={"detail": "Not authenticated"}
    )

# Ensure directories exist
Path("/data").mkdir(exist_ok=True)
Path(settings.NAS_WATCH_PATH).mkdir(parents=True, exist_ok=True)
Path(settings.NAS_ARCHIVE_PATH).mkdir(parents=True, exist_ok=True)
Path(settings.NAS_QUARANTINE_PATH).mkdir(parents=True, exist_ok=True)


# Models
class LoginRequest(BaseModel):
    username: str
    password: str


class RetryRequest(BaseModel):
    record_id: int


class EmailRequest(BaseModel):
    record_id: int
    email: str


# Auth endpoints
@app.post("/api/auth/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login endpoint."""
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    # Create token
    access_token = create_access_token(data={"sub": user.username})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role
    }


@app.post("/api/verify-token")
async def verify_token(current_user: User = Depends(get_current_user)):
    """Verify JWT token for web interface."""
    return {
        "valid": True,
        "username": current_user.username,
        "role": current_user.role
    }


# API endpoints
@app.get("/api/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get statistics."""
    total = await db.execute(select(func.count(FileRecord.id)))
    total_count = total.scalar()
    
    completed = await db.execute(
        select(func.count(FileRecord.id)).where(FileRecord.status == "completed")
    )
    completed_count = completed.scalar()
    
    failed = await db.execute(
        select(func.count(FileRecord.id)).where(FileRecord.status == "failed")
    )
    failed_count = failed.scalar()
    
    pending = await db.execute(
        select(func.count(FileRecord.id)).where(FileRecord.status == "pending")
    )
    pending_count = pending.scalar()
    
    return {
        "total": total_count,
        "completed": completed_count,
        "failed": failed_count,
        "pending": pending_count
    }


@app.get("/api/records")
async def get_records(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get file records."""
    query = select(FileRecord).order_by(desc(FileRecord.created_at))
    
    if status:
        query = query.where(FileRecord.status == status)
    
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    return [
        {
            "id": r.id,
            "order_no": r.order_no,
            "file_name": r.file_name,
            "status": r.status,
            "sent_to_1c": r.sent_to_1c,
            "sent_to_1c_at": r.sent_to_1c_at.isoformat() if r.sent_to_1c_at else None,
            "email_sent": r.email_sent,
            "patient_email": r.patient_email,
            "created_at": r.created_at.isoformat(),
            "error_message": r.error_message
        }
        for r in records
    ]


@app.get("/api/logs")
async def get_logs(
    record_id: Optional[int] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get audit logs."""
    query = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)
    
    if record_id:
        query = query.where(AuditLog.record_id == record_id)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return [
        {
            "id": l.id,
            "record_id": l.record_id,
            "action": l.action,
            "status": l.status,
            "message": l.message,
            "created_at": l.created_at.isoformat()
        }
        for l in logs
    ]


@app.post("/api/retry")
async def retry_processing(
    request: RetryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry processing a failed record."""
    result = await db.execute(
        select(FileRecord).where(FileRecord.id == request.record_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    # Reset status
    record.status = "pending"
    record.retry_count = 0
    record.error_message = None
    await db.commit()
    
    # Try to send to 1C
    success = await send_to_1c(record, db)
    
    return {"success": success, "record_id": record.id}


@app.post("/api/send-email")
async def resend_email(
    request: EmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resend email."""
    result = await db.execute(
        select(FileRecord).where(FileRecord.id == request.record_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    success = await send_email(record, db, request.email)
    
    if success:
        record.email_sent = True
        record.email_sent_at = datetime.utcnow()
        record.patient_email = request.email
        await db.commit()
    
    return {"success": success}


@app.get("/api/file/{record_id}")
async def get_file(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get PDF file."""
    result = await db.execute(
        select(FileRecord).where(FileRecord.id == record_id)
    )
    record = result.scalar_one_or_none()
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    file_path = Path(record.file_path)
    if not file_path.exists():
        # Try archive
        date_str = record.archived_at.strftime("%Y-%m-%d") if record.archived_at else datetime.now().strftime("%Y-%m-%d")
        archive_path = Path(settings.NAS_ARCHIVE_PATH) / date_str / record.file_name
        if archive_path.exists():
            file_path = archive_path
        else:
            raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=record.file_name
    )


@app.post("/api/test-pdf-parser")
async def test_pdf_parser(
    file_path: str,
    current_user: User = Depends(get_current_user)
):
    """Test PDF parser on a specific file."""
    try:
        from pathlib import Path
        if not Path(file_path).exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        result = parse_lab_result_pdf(file_path)
        return {
            "success": True,
            "file_path": file_path,
            "parsed_data": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/test-1c-connection")
async def test_1c_connection(current_user: User = Depends(get_current_user)):
    """Test 1C connection."""
    integrator = get_1c_integrator()
    result = integrator.test_connection()
    return result


@app.post("/api/test-full-chain")
async def test_full_chain(
    file_path: str,
    current_user: User = Depends(get_current_user)
):
    """Test full chain: PDF → Parse → Send to 1C."""
    try:
        from pathlib import Path
        if not Path(file_path).exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        # 1. Parse PDF
        parsed_data = parse_lab_result_pdf(file_path)
        
        # 2. Send to 1C
        integrator = get_1c_integrator()
        send_result = integrator.fill_template(parsed_data)
        
        return {
            "success": send_result.get("success", False),
            "file_path": file_path,
            "parsed_data": parsed_data,
            "send_to_1c_result": send_result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Static files (no auth required)
@app.get("/debug.html", response_class=HTMLResponse)
async def debug_page():
    """Debug page for testing."""
    with open("debug.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content)

@app.get("/test-auth.html", response_class=HTMLResponse)
async def test_auth_page():
    """Test authentication page."""
    with open("test-auth.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content)

@app.get("/simple-test.html", response_class=HTMLResponse)
async def simple_test_page():
    """Simple test page."""
    with open("simple-test.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content)

@app.get("/test.html", response_class=HTMLResponse)
async def root_test_page():
    """Root test page."""
    with open("test.html", "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content)


# Optional authentication - only validates token if provided
async def get_current_user_optional(
    token: Optional[str] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """Get current user if token is provided and valid."""
    if not token:
        return None

    try:
        payload = jwt.decode(token.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except JWTError:
        return None

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    return user if user else None

# Web UI endpoints
@app.get("/")
async def root():
    """Redirect to login page."""
    return RedirectResponse(url="/login", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Main dashboard page - auth check done in JavaScript."""
    # Return page without auth check - JS will handle token validation
    return templates.TemplateResponse("index.html", {
        "request": request,
        "stats": {"total": 0, "completed": 0, "failed": 0, "pending": 0},
        "current_user": None
    })


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/records", response_class=HTMLResponse)
async def records_page(request: Request):
    """Records page - auth check done in JavaScript."""
    return templates.TemplateResponse("records.html", {"request": request})


@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Logs page - auth check done in JavaScript."""
    return templates.TemplateResponse("logs.html", {"request": request})


# Health check
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

