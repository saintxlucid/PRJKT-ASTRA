"""
Database models and session management.

This module provides SQLAlchemy models for conversations and messages,
along with database session management with connection pooling and
SQLite WAL mode for improved concurrency.
"""

from __future__ import annotations

import os
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker
from sqlalchemy.pool import QueuePool

from astra.utils.errors import DatabaseConnectionError, DatabaseQueryError
from astra.utils.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models"""

    pass


class Conversation(Base):
    """Conversation model"""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to messages
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, conversation_id={self.conversation_id}, title={self.title})>"


class Message(Base):
    """Message model"""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(255), ForeignKey("conversations.conversation_id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # system, user, assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to conversation
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"


class DatabaseManager:
    """
    Database manager for handling connections and sessions.

    Provides context managers for database operations.
    """

    def __init__(self, database_url: str, echo: bool = False):
        """
        Initialize database manager with connection pooling.

        Args:
            database_url: SQLAlchemy database URL
            echo: If True, log all SQL statements
        """
        self.database_url = database_url
        self.echo = echo

        try:
            # Get pool configuration from environment
            pool_size = int(os.getenv("ASTRA_DATABASE_POOL_SIZE", "20"))
            max_overflow = int(os.getenv("ASTRA_DATABASE_MAX_OVERFLOW", "40"))
            pool_timeout = int(os.getenv("ASTRA_DATABASE_POOL_TIMEOUT", "30"))
            
            # SQLite-specific configuration
            connect_args = {}
            if database_url.startswith("sqlite"):
                connect_args = {"check_same_thread": False}
            
            # Create engine with connection pooling
            self.engine = create_engine(
                database_url,
                echo=echo,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_recycle=1800,  # Recycle connections after 30 minutes
                connect_args=connect_args,
            )
            
            # Enable SQLite WAL mode for better concurrency
            if database_url.startswith("sqlite"):
                @event.listens_for(self.engine, "connect")
                def _sqlite_pragma(dbapi_conn, _):
                    cursor = dbapi_conn.cursor()
                    cursor.execute("PRAGMA journal_mode=WAL;")
                    cursor.execute("PRAGMA synchronous=NORMAL;")
                    cursor.execute("PRAGMA temp_store=MEMORY;")
                    cursor.execute("PRAGMA mmap_size=268435456;")  # 256MB mmap
                    cursor.close()
            
            self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
            logger.info(
                "database_initialized",
                database_url=database_url,
                pool_size=pool_size,
                max_overflow=max_overflow,
                wal_enabled=database_url.startswith("sqlite"),
            )
        except Exception as e:
            logger.error("database_initialization_failed", error=str(e))
            raise DatabaseConnectionError(f"Failed to initialize database: {e}") from e

    def create_tables(self):
        """Create all tables in the database"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("database_tables_created")
        except Exception as e:
            logger.error("database_table_creation_failed", error=str(e))
            raise DatabaseQueryError(f"Failed to create tables: {e}") from e

    def get_session(self) -> Session:
        """
        Get a new database session.

        Returns:
            SQLAlchemy session

        Usage:
            session = db_manager.get_session()
            try:
                # do work
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        """
        return self.SessionLocal()

    def close(self):
        """Close database connection"""
        self.engine.dispose()
        logger.info("database_closed")
