"""
Database Connection and Session Management for Punjab Air Quality Relational Core.
Supports PostgreSQL 16 with psycopg driver and SQLite for zero-config portable testing.
"""
from contextlib import contextmanager
import logging
import os
from pathlib import Path
from typing import Any, Generator, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker, Session

logger = logging.getLogger("paq.database")

Base = declarative_base()


class DatabaseConfig:
    """Configuration loader for Relational Core and TimescaleDB."""

    def __init__(self) -> None:
        self.use_db: bool = os.getenv("USE_DATABASE_BACKEND", "true").lower() in ("true", "1", "yes")
        
        # Primary connection URL
        self.database_url: Optional[str] = os.getenv("DATABASE_URL")
        
        # Explicit connection parts fallback
        self.host: str = os.getenv("POSTGRES_HOST", "127.0.0.1")
        self.port: int = int(os.getenv("POSTGRES_PORT", "5433"))
        self.user: str = os.getenv("POSTGRES_USER", "postgres")
        self.password: str = os.getenv("POSTGRES_PASSWORD", "")
        self.database: str = os.getenv("POSTGRES_DB", "punjab_air_quality")
        
        if not self.database_url:
            if self.password:
                self.database_url = f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            else:
                self.database_url = f"postgresql+psycopg://{self.user}@{self.host}:{self.port}/{self.database}"

        # Pool settings
        self.pool_size: int = int(os.getenv("DB_POOL_SIZE", "10"))
        self.max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.pool_timeout: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))


class DatabaseManager:
    """Manages SQLAlchemy Engine, Session pooling, and database health probes."""

    _instance: Optional["DatabaseManager"] = None

    def __init__(self, config: Optional[DatabaseConfig] = None) -> None:
        self.config = config or DatabaseConfig()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[scoped_session] = None
        self._is_connected: bool = False
        self._initialize_engine()

    @classmethod
    def get_instance(cls, config: Optional[DatabaseConfig] = None) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = cls(config=config)
        return cls._instance

    def _initialize_engine(self) -> None:
        """Initializes SQLAlchemy Engine with connection pooling and test fallback."""
        if not self.config.use_db:
            logger.info("Database backend disabled via USE_DATABASE_BACKEND=false.")
            return

        db_url = self.config.database_url
        try:
            connect_args = {}
            if db_url and db_url.startswith("postgresql"):
                connect_args = {"connect_timeout": 3}
                self._engine = create_engine(
                    db_url,
                    pool_size=self.config.pool_size,
                    max_overflow=self.config.max_overflow,
                    pool_timeout=self.config.pool_timeout,
                    pool_pre_ping=True,
                    connect_args=connect_args,
                )
            elif db_url and db_url.startswith("sqlite"):
                self._engine = create_engine(
                    db_url,
                    connect_args={"check_same_thread": False},
                )
            else:
                self._engine = create_engine(db_url, pool_pre_ping=True)

            # Test connection
            with self._engine.connect() as conn:
                res = conn.execute(text("SELECT 1")).scalar()
                if res == 1:
                    self._is_connected = True
                    logger.info(f"DatabaseManager successfully connected to {db_url}")

            self._session_factory = scoped_session(
                sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
            )

        except Exception as e:
            logger.warning(
                f"Failed to connect to primary database ({db_url}): {e}. "
                "Falling back to SQLite in-memory engine for local execution."
            )
            try:
                # Fallback to SQLite in-memory engine so SQL ORM operations function everywhere
                self._engine = create_engine(
                    "sqlite:///:memory:",
                    connect_args={"check_same_thread": False},
                )
                self._session_factory = scoped_session(
                    sessionmaker(autocommit=False, autoflush=False, bind=self._engine)
                )
                self._is_connected = True
                logger.info("Initialized fallback SQLite in-memory database engine.")
            except Exception as fallback_err:
                logger.error(f"Failed to initialize fallback database: {fallback_err}")
                self._is_connected = False

    @property
    def engine(self) -> Optional[Engine]:
        return self._engine

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def ping(self) -> bool:
        """Executes lightweight liveness query."""
        if not self._engine:
            return False
        try:
            with self._engine.connect() as conn:
                return conn.execute(text("SELECT 1")).scalar() == 1
        except Exception:
            return False

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Provides transactional scope around a series of operations."""
        if not self._session_factory:
            raise RuntimeError("Database session factory is not initialized.")
        session: Session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    session_scope = get_session


    def close(self) -> None:
        """Disposes connection pool upon application shutdown."""
        if self._session_factory:
            self._session_factory.remove()
        if self._engine:
            self._engine.dispose()
            self._is_connected = False
            logger.info("DatabaseManager connection pool disposed.")
