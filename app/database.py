"""Database models and connection."""
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base as async_declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:////data/lis.db")
# Convert sqlite:/// to sqlite+aiosqlite:/// for async
ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")

engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class FileRecord(Base):
    """Запись о файле результата анализа."""
    __tablename__ = "file_records"

    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(50), index=True, nullable=False)  # Номер исследования
    file_name = Column(String(255), nullable=False)
    file_hash = Column(String(64), unique=True, nullable=False)  # SHA256
    file_path = Column(String(512))
    
    # Статусы обработки
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    
    # Интеграция с 1С
    sent_to_1c = Column(Boolean, default=False)
    sent_to_1c_at = Column(DateTime, nullable=True)
    doc_ref_1c = Column(String(255), nullable=True)
    
    # Email
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    patient_email = Column(String(255), nullable=True)
    
    # Аудит
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    archived_at = Column(DateTime, nullable=True)
    
    # Ошибки
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)


class AuditLog(Base):
    """Журнал аудита всех операций."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, nullable=True)  # FK to FileRecord
    action = Column(String(50), nullable=False)  # file_detected, sent_to_1c, email_sent, etc.
    status = Column(String(20), nullable=False)  # success, error
    message = Column(Text)
    details = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    """Пользователи системы."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="operator")  # administrator, operator
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


async def init_db():
    """Инициализация базы данных."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency для получения сессии БД."""
    async with SessionLocal() as session:
        yield session

