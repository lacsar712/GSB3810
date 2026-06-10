from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_roles
from app.models import (
    BackupRecord,
    BackupStatus,
    DataDictionary,
    QuestionBankResource,
    User,
    UserRole,
)
from app.schemas import (
    BackupResponse,
    DictionaryCreate,
    DictionaryResponse,
    MessageResponse,
    QuestionResourceCreate,
    QuestionResourceResponse,
    QuestionResourceUpdate,
    SystemConfigResponse,
    SystemConfigUpdate,
    TeacherCreate,
    TeacherResponse,
    TeacherStatusUpdate,
    TeacherUpdate,
)
from app.security import hash_password
from app.services import audit_log, dump_database_snapshot, read_snapshot_file, restore_database_snapshot, write_snapshot_file
from app.models import SystemConfig


router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/teachers", response_model=list[TeacherResponse])
def list_teachers(
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[TeacherResponse]:
    query = db.query(User).filter(User.role == UserRole.TEACHER)
    if keyword:
        query = query.filter((User.username.like(f"%{keyword}%")) | (User.full_name.like(f"%{keyword}%")))
    teachers = query.order_by(User.created_at.desc()).all()
    return [TeacherResponse.model_validate(teacher) for teacher in teachers]


@router.post("/teachers", response_model=TeacherResponse)
def create_teacher(
    payload: TeacherCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> TeacherResponse:
    existed = db.query(User).filter(User.username == payload.username).first()
    if existed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="教师账号已存在")

    teacher = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=UserRole.TEACHER,
        full_name=payload.full_name,
        mobile=payload.mobile,
        permissions=payload.permissions,
        is_active=True,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)

    audit_log(db, current_user.id, "teacher", "create", f"create teacher {teacher.username}")
    return TeacherResponse.model_validate(teacher)


@router.put("/teachers/{teacher_id}", response_model=TeacherResponse)
def update_teacher(
    teacher_id: int,
    payload: TeacherUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> TeacherResponse:
    teacher = db.query(User).filter(User.id == teacher_id, User.role == UserRole.TEACHER).first()
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教师账号不存在")

    teacher.full_name = payload.full_name
    teacher.mobile = payload.mobile
    teacher.permissions = payload.permissions

    db.commit()
    db.refresh(teacher)
    audit_log(db, current_user.id, "teacher", "update", f"update teacher {teacher.username}")
    return TeacherResponse.model_validate(teacher)


@router.patch("/teachers/{teacher_id}/status", response_model=TeacherResponse)
def toggle_teacher_status(
    teacher_id: int,
    payload: TeacherStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> TeacherResponse:
    teacher = db.query(User).filter(User.id == teacher_id, User.role == UserRole.TEACHER).first()
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="教师账号不存在")

    teacher.is_active = payload.is_active
    db.commit()
    db.refresh(teacher)
    audit_log(db, current_user.id, "teacher", "toggle_status", f"teacher {teacher.username}: {payload.is_active}")
    return TeacherResponse.model_validate(teacher)


@router.get("/question-resources", response_model=list[QuestionResourceResponse])
def list_question_resources(
    keyword: str | None = Query(default=None),
    subject: str | None = Query(default=None),
    grade: str | None = Query(default=None),
    status_value: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[QuestionResourceResponse]:
    query = db.query(QuestionBankResource)
    if keyword:
        query = query.filter(QuestionBankResource.title.like(f"%{keyword}%"))
    if subject:
        query = query.filter(QuestionBankResource.subject == subject)
    if grade:
        query = query.filter(QuestionBankResource.grade == grade)
    if status_value:
        query = query.filter(QuestionBankResource.status == status_value)
    rows = query.order_by(QuestionBankResource.created_at.desc()).all()
    return [QuestionResourceResponse.model_validate(row, from_attributes=True) for row in rows]


@router.post("/question-resources", response_model=QuestionResourceResponse)
def create_question_resource(
    payload: QuestionResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> QuestionResourceResponse:
    resource = QuestionBankResource(
        title=payload.title,
        subject=payload.subject,
        grade=payload.grade,
        tags=payload.tags,
        description=payload.description,
        resource_url=payload.resource_url,
        publisher_id=current_user.id,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    audit_log(db, current_user.id, "question_bank", "create", f"resource {resource.title}")
    return QuestionResourceResponse.model_validate(resource, from_attributes=True)


@router.put("/question-resources/{resource_id}", response_model=QuestionResourceResponse)
def update_question_resource(
    resource_id: int,
    payload: QuestionResourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> QuestionResourceResponse:
    resource = db.query(QuestionBankResource).filter(QuestionBankResource.id == resource_id).first()
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库资源不存在")

    resource.title = payload.title
    resource.subject = payload.subject
    resource.grade = payload.grade
    resource.tags = payload.tags
    resource.description = payload.description
    resource.resource_url = payload.resource_url
    resource.status = payload.status

    db.commit()
    db.refresh(resource)
    audit_log(db, current_user.id, "question_bank", "update", f"resource {resource.id}")
    return QuestionResourceResponse.model_validate(resource, from_attributes=True)


@router.delete("/question-resources/{resource_id}", response_model=MessageResponse)
def delete_question_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    resource = db.query(QuestionBankResource).filter(QuestionBankResource.id == resource_id).first()
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题库资源不存在")

    db.delete(resource)
    db.commit()
    audit_log(db, current_user.id, "question_bank", "delete", f"resource {resource_id}")
    return MessageResponse(message="题库资源已删除")


@router.get("/configs", response_model=list[SystemConfigResponse])
def list_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[SystemConfigResponse]:
    rows = db.query(SystemConfig).order_by(SystemConfig.config_key.asc()).all()
    return [SystemConfigResponse.model_validate(row, from_attributes=True) for row in rows]


@router.put("/configs/{config_key}", response_model=SystemConfigResponse)
def update_config(
    config_key: str,
    payload: SystemConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> SystemConfigResponse:
    config = db.query(SystemConfig).filter(SystemConfig.config_key == config_key).first()
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="配置项不存在")

    config.config_value = payload.config_value
    config.updated_by = current_user.id
    db.commit()
    db.refresh(config)
    audit_log(db, current_user.id, "system", "update_config", config_key)
    return SystemConfigResponse.model_validate(config, from_attributes=True)


@router.get("/dictionaries", response_model=list[DictionaryResponse])
def list_dictionary(
    dict_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[DictionaryResponse]:
    query = db.query(DataDictionary)
    if dict_type:
        query = query.filter(DataDictionary.dict_type == dict_type)
    rows = query.order_by(DataDictionary.dict_type.asc(), DataDictionary.sort_order.asc()).all()
    return [DictionaryResponse.model_validate(row) for row in rows]


@router.post("/dictionaries", response_model=DictionaryResponse)
def create_dictionary(
    payload: DictionaryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> DictionaryResponse:
    existed = (
        db.query(DataDictionary)
        .filter(DataDictionary.dict_type == payload.dict_type, DataDictionary.dict_key == payload.dict_key)
        .first()
    )
    if existed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="字典键已存在")

    record = DataDictionary(
        dict_type=payload.dict_type,
        dict_key=payload.dict_key,
        dict_value=payload.dict_value,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    audit_log(db, current_user.id, "system", "create_dictionary", f"{record.dict_type}:{record.dict_key}")
    return DictionaryResponse.model_validate(record)


@router.get("/backups", response_model=list[BackupResponse])
def list_backups(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> list[BackupResponse]:
    rows = db.query(BackupRecord).order_by(BackupRecord.created_at.desc()).all()
    return [BackupResponse.model_validate(row, from_attributes=True) for row in rows]


@router.post("/backups", response_model=BackupResponse)
def create_backup(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> BackupResponse:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"school_backup_{timestamp}.json"
    snapshot = dump_database_snapshot()
    file_path = write_snapshot_file(snapshot, filename)

    record = BackupRecord(
        file_name=filename,
        file_path=file_path,
        status=BackupStatus.READY,
        created_by=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    audit_log(db, current_user.id, "backup", "create", filename)
    return BackupResponse.model_validate(record, from_attributes=True)


@router.post("/backups/{backup_id}/restore", response_model=MessageResponse)
def restore_backup(
    backup_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
) -> MessageResponse:
    record = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="备份记录不存在")

    snapshot = read_snapshot_file(record.file_path)
    restore_database_snapshot(db, snapshot)

    refreshed = db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
    if refreshed:
        refreshed.status = BackupStatus.RESTORED
        refreshed.restored_by = current_user.id
        refreshed.restored_at = datetime.now()
        db.commit()

    audit_log(db, current_user.id, "backup", "restore", record.file_name)
    return MessageResponse(message="备份已恢复")
