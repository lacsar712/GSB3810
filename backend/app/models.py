from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"
    PARENT = "PARENT"


class BehaviorCategory(str, Enum):
    REWARD = "REWARD"
    PUNISHMENT = "PUNISHMENT"
    OBSERVATION = "OBSERVATION"


class NoticeType(str, Enum):
    CLASS = "CLASS"
    PERSONAL = "PERSONAL"
    ANNOUNCEMENT = "ANNOUNCEMENT"
    RESOURCE = "RESOURCE"


class QuestionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class BackupStatus(str, Enum):
    READY = "READY"
    RESTORED = "RESTORED"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole, native_enum=False), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    mobile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    wechat_openid: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ClassRoom(Base):
    __tablename__ = "class_rooms"
    __table_args__ = (UniqueConstraint("name", "academic_year", name="uq_class_name_year"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    grade: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    homeroom_teacher_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    homeroom_teacher: Mapped[User | None] = relationship()


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    student_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("class_rooms.id"), nullable=False, index=True)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    enrollment_year: Mapped[int] = mapped_column(Integer, nullable=False)
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    guardian_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship()
    class_room: Mapped[ClassRoom] = relationship()


class ParentStudentRelation(Base):
    __tablename__ = "parent_student_relations"
    __table_args__ = (UniqueConstraint("parent_id", "student_id", name="uq_parent_student"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    relation_label: Mapped[str] = mapped_column(String(20), nullable=False)

    parent: Mapped[User] = relationship(foreign_keys=[parent_id])
    student: Mapped[StudentProfile] = relationship(foreign_keys=[student_id])


class BehaviorRecord(Base):
    __tablename__ = "behavior_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student_profiles.id", ondelete="CASCADE"), index=True, nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    category: Mapped[BehaviorCategory] = mapped_column(
        SQLEnum(BehaviorCategory, native_enum=False),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    score_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    student: Mapped[StudentProfile] = relationship()
    teacher: Mapped[User] = relationship()


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    grade: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("class_rooms.id"), nullable=False)
    exam_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    class_room: Mapped[ClassRoom] = relationship()


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = (UniqueConstraint("exam_id", "student_id", name="uq_exam_student"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    comment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    exam: Mapped[Exam] = relationship()
    student: Mapped[StudentProfile] = relationship()


class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    notice_type: Mapped[NoticeType] = mapped_column(
        SQLEnum(NoticeType, native_enum=False),
        nullable=False,
        index=True,
    )
    publisher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    class_id: Mapped[int | None] = mapped_column(ForeignKey("class_rooms.id"), nullable=True)
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    publisher: Mapped[User] = relationship(foreign_keys=[publisher_id])


class QuestionBankResource(Base):
    __tablename__ = "question_bank_resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    grade: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    tags: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resource_url: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[QuestionStatus] = mapped_column(
        SQLEnum(QuestionStatus, native_enum=False),
        nullable=False,
        default=QuestionStatus.ACTIVE,
        index=True,
    )
    publisher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SystemConfig(Base):
    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    config_key: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DataDictionary(Base):
    __tablename__ = "data_dictionaries"
    __table_args__ = (UniqueConstraint("dict_type", "dict_key", name="uq_dict_type_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dict_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    dict_key: Mapped[str] = mapped_column(String(50), nullable=False)
    dict_value: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class BackupRecord(Base):
    __tablename__ = "backup_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(String(120), nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[BackupStatus] = mapped_column(
        SQLEnum(BackupStatus, native_enum=False),
        nullable=False,
        default=BackupStatus.READY,
        index=True,
    )
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    restored_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    restored_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    module: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
