"""SQLAlchemy ORM models for the SAP Data Migration Governance Platform."""

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class User(Base):
    """Application user with a single assigned role."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    validation_runs: Mapped[list["ValidationRun"]] = relationship(back_populates="user")


class Stream(Base):
    """Top-level migration stream (e.g. O2C, P2P, R2R)."""

    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    objects: Mapped[list["MigrationObject"]] = relationship(
        back_populates="stream", cascade="all, delete-orphan"
    )


class MigrationObject(Base):
    """Migration object belonging to a stream (e.g. Business Partner, CMIR)."""

    __tablename__ = "objects"
    __table_args__ = (UniqueConstraint("stream_id", "object_name", name="uq_stream_object"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id"), nullable=False, index=True)
    object_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    stream: Mapped["Stream"] = relationship(back_populates="objects")
    functional_specs: Mapped[list["FunctionalSpec"]] = relationship(
        back_populates="object_", cascade="all, delete-orphan"
    )
    validation_rules: Mapped[list["ValidationRule"]] = relationship(
        back_populates="object_", cascade="all, delete-orphan"
    )
    validation_runs: Mapped[list["ValidationRun"]] = relationship(
        back_populates="object_", cascade="all, delete-orphan"
    )


class FunctionalSpec(Base):
    """A versioned MDM Functional Specification document for an object."""

    __tablename__ = "functional_specs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    file_name: Mapped[str] = mapped_column(String(255), default="")
    file_path: Mapped[str] = mapped_column(String(512), default="")
    is_active: Mapped[bool] = mapped_column(default=True)
    upload_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    object_: Mapped["MigrationObject"] = relationship(back_populates="functional_specs")
    rules: Mapped[list["ValidationRule"]] = relationship(
        back_populates="spec", cascade="all, delete-orphan"
    )


class ValidationRule(Base):
    """Stored validation rules (JSON) extracted from a Functional Specification."""

    __tablename__ = "validation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_id: Mapped[int] = mapped_column(ForeignKey("objects.id"), nullable=False, index=True)
    spec_id: Mapped[int | None] = mapped_column(ForeignKey("functional_specs.id"), nullable=True)
    rule_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    object_: Mapped["MigrationObject"] = relationship(back_populates="validation_rules")
    spec: Mapped["FunctionalSpec"] = relationship(back_populates="rules")


class ValidationRun(Base):
    """A single validation execution against an object's rules."""

    __tablename__ = "validation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    object_id: Mapped[int | None] = mapped_column(ForeignKey("objects.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    run_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    passed_records: Mapped[int] = mapped_column(Integer, default=0)
    failed_records: Mapped[int] = mapped_column(Integer, default=0)
    failure_detail_json: Mapped[str] = mapped_column(Text, default="[]")

    object_: Mapped["MigrationObject"] = relationship(back_populates="validation_runs")
    user: Mapped["User"] = relationship(back_populates="validation_runs")


class AuditLog(Base):
    """Audit trail of significant user actions across the platform."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    username: Mapped[str] = mapped_column(String(80), default="")
    role: Mapped[str] = mapped_column(String(40), default="")
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
