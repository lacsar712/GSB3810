from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from app.models import BehaviorCategory, BackupStatus, NoticeType, QuestionStatus, UserRole


class MessageResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=64)


class WechatLoginRequest(BaseModel):
    code: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=20)
    student_no: str | None = Field(
        default=None,
        max_length=30,
        validation_alias=AliasChoices("student_no", "studentNo"),
    )


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole
    full_name: str
    mobile: str | None
    is_active: bool
    permissions: list[str]


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserBrief


class TeacherCreate(BaseModel):
    username: str = Field(min_length=4, max_length=50)
    password: str = Field(min_length=6, max_length=64)
    full_name: str = Field(min_length=2, max_length=100)
    mobile: str | None = Field(default=None, max_length=20)
    permissions: list[str] = Field(default_factory=list)


class TeacherUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    mobile: str | None = Field(default=None, max_length=20)
    permissions: list[str] = Field(default_factory=list)


class TeacherStatusUpdate(BaseModel):
    is_active: bool


class TeacherResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole
    full_name: str
    mobile: str | None
    is_active: bool
    permissions: list[str]
    created_at: datetime


class ClassRoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    grade: str
    academic_year: str


class StudentUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    gender: str = Field(min_length=1, max_length=10)
    birth_date: date | None = None
    enrollment_year: int = Field(ge=2000, le=2100)
    address: str | None = Field(default=None, max_length=200)
    guardian_note: str | None = Field(default=None, max_length=500)
    class_id: int


class StudentResponse(BaseModel):
    id: int
    user_id: int
    student_no: str
    full_name: str
    gender: str
    class_id: int
    class_name: str
    grade: str
    enrollment_year: int
    address: str | None
    guardian_note: str | None


class BehaviorCreate(BaseModel):
    student_id: int
    category: BehaviorCategory
    title: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=4, max_length=500)
    score_delta: int = Field(ge=-20, le=20)
    record_date: date


class BehaviorResponse(BaseModel):
    id: int
    student_id: int
    student_name: str
    category: BehaviorCategory
    title: str
    description: str
    score_delta: int
    record_date: date
    teacher_name: str


class ExamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    exam_type: str = Field(min_length=2, max_length=30)
    subject: str = Field(min_length=1, max_length=30)
    grade: str = Field(min_length=1, max_length=20)
    class_id: int
    exam_date: date


class ExamResponse(BaseModel):
    id: int
    name: str
    exam_type: str
    subject: str
    grade: str
    class_id: int
    class_name: str
    exam_date: date
    is_published: bool


class ScoreInput(BaseModel):
    student_id: int
    score: Decimal = Field(ge=0, le=100)
    comment: str | None = Field(default=None, max_length=255)


class ScoreBatchUpsert(BaseModel):
    scores: list[ScoreInput] = Field(default_factory=list, min_length=1)


class ScoreResponse(BaseModel):
    id: int
    exam_id: int
    student_id: int
    student_name: str
    score: Decimal
    rank: int | None
    comment: str | None


class NoticeCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    content: str = Field(min_length=4, max_length=2000)
    notice_type: NoticeType
    class_id: int | None = None
    target_user_id: int | None = None


class NoticeResponse(BaseModel):
    id: int
    title: str
    content: str
    notice_type: NoticeType
    class_id: int | None
    target_user_id: int | None
    publisher_name: str
    created_at: datetime


class QuestionResourceCreate(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    subject: str = Field(min_length=1, max_length=30)
    grade: str = Field(min_length=1, max_length=20)
    tags: str | None = Field(default=None, max_length=200)
    description: str = Field(min_length=4, max_length=2000)
    resource_url: str = Field(min_length=6, max_length=255)


class QuestionResourceUpdate(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    subject: str = Field(min_length=1, max_length=30)
    grade: str = Field(min_length=1, max_length=20)
    tags: str | None = Field(default=None, max_length=200)
    description: str = Field(min_length=4, max_length=2000)
    resource_url: str = Field(min_length=6, max_length=255)
    status: QuestionStatus


class QuestionResourceResponse(BaseModel):
    id: int
    title: str
    subject: str
    grade: str
    tags: str | None
    description: str
    resource_url: str
    status: QuestionStatus
    created_at: datetime


class SystemConfigResponse(BaseModel):
    id: int
    config_key: str
    config_value: str
    description: str
    updated_at: datetime


class SystemConfigUpdate(BaseModel):
    config_value: str = Field(min_length=1, max_length=2000)


class DictionaryCreate(BaseModel):
    dict_type: str = Field(min_length=1, max_length=50)
    dict_key: str = Field(min_length=1, max_length=50)
    dict_value: str = Field(min_length=1, max_length=100)
    sort_order: int = Field(default=0, ge=0, le=999)
    is_active: bool = True


class DictionaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dict_type: str
    dict_key: str
    dict_value: str
    sort_order: int
    is_active: bool


class BackupResponse(BaseModel):
    id: int
    file_name: str
    file_path: str
    status: BackupStatus
    created_at: datetime
    restored_at: datetime | None


class ClassAverageItem(BaseModel):
    subject: str
    average_score: float


class TrendItem(BaseModel):
    exam_name: str
    exam_date: date
    score: float
    rank: int | None


class SubjectBalanceItem(BaseModel):
    subject: str
    score: float


class MiniProfile(BaseModel):
    student_id: int
    student_name: str
    student_no: str
    class_name: str
    grade: str


class MiniScoreItem(BaseModel):
    exam_name: str
    subject: str
    exam_date: date
    score: float
    rank: int | None


class MiniBehaviorItem(BaseModel):
    category: BehaviorCategory
    title: str
    description: str
    score_delta: int
    record_date: date


class MiniNoticeItem(BaseModel):
    title: str
    content: str
    notice_type: NoticeType
    created_at: datetime
