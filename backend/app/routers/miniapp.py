from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import Notice, NoticeType, ParentStudentRelation, Score, StudentProfile, User, UserRole
from app.schemas import MiniBehaviorItem, MiniNoticeItem, MiniProfile, MiniScoreItem, TrendItem
from app.models import BehaviorRecord, Exam


router = APIRouter(prefix="/api/mini", tags=["MiniApp"])


def _resolve_student_for_mini(
    db: Session,
    current_user: User,
    student_id: int | None = None,
) -> StudentProfile:
    if current_user.role == UserRole.STUDENT:
        student = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
        if student is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生档案不存在")
        return student

    if current_user.role != UserRole.PARENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅支持家长或学生访问")

    relations = db.query(ParentStudentRelation).filter(ParentStudentRelation.parent_id == current_user.id).all()
    if not relations:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="家长账号未绑定学生")

    if student_id is not None:
        relation = next((item for item in relations if item.student_id == student_id), None)
        if relation is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该学生信息")
        return relation.student

    return relations[0].student


@router.get("/profile", response_model=MiniProfile)
def get_profile(
    student_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MiniProfile:
    student = _resolve_student_for_mini(db, current_user, student_id)
    return MiniProfile(
        student_id=student.id,
        student_name=student.user.full_name,
        student_no=student.student_no,
        class_name=student.class_room.name,
        grade=student.class_room.grade,
    )


@router.get("/scores", response_model=list[MiniScoreItem])
def get_scores(
    student_id: int | None = Query(default=None),
    subject: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MiniScoreItem]:
    student = _resolve_student_for_mini(db, current_user, student_id)

    query = (
        db.query(Score, Exam)
        .join(Exam, Exam.id == Score.exam_id)
        .filter(Score.student_id == student.id, Exam.is_published.is_(True))
    )
    if subject:
        query = query.filter(Exam.subject == subject)
    rows = query.order_by(Exam.exam_date.desc()).all()
    return [
        MiniScoreItem(
            exam_name=exam.name,
            subject=exam.subject,
            exam_date=exam.exam_date,
            score=float(score.score),
            rank=score.rank,
        )
        for score, exam in rows
    ]


@router.get("/score-trend", response_model=list[TrendItem])
def get_score_trend(
    subject: str,
    student_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TrendItem]:
    student = _resolve_student_for_mini(db, current_user, student_id)
    rows = (
        db.query(Score, Exam)
        .join(Exam, Exam.id == Score.exam_id)
        .filter(Score.student_id == student.id, Exam.subject == subject, Exam.is_published.is_(True))
        .order_by(Exam.exam_date.asc())
        .all()
    )
    return [
        TrendItem(
            exam_name=exam.name,
            exam_date=exam.exam_date,
            score=float(score.score),
            rank=score.rank,
        )
        for score, exam in rows
    ]


@router.get("/behaviors", response_model=list[MiniBehaviorItem])
def get_behaviors(
    student_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MiniBehaviorItem]:
    student = _resolve_student_for_mini(db, current_user, student_id)
    rows = (
        db.query(BehaviorRecord)
        .filter(BehaviorRecord.student_id == student.id)
        .order_by(BehaviorRecord.record_date.desc(), BehaviorRecord.id.desc())
        .all()
    )
    return [
        MiniBehaviorItem(
            category=row.category,
            title=row.title,
            description=row.description,
            score_delta=row.score_delta,
            record_date=row.record_date,
        )
        for row in rows
    ]


@router.get("/notices", response_model=list[MiniNoticeItem])
def get_notices(
    student_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MiniNoticeItem]:
    student = _resolve_student_for_mini(db, current_user, student_id)

    student_user_id = student.user_id
    rows = (
        db.query(Notice)
        .filter(
            Notice.is_published.is_(True),
            or_(
                Notice.class_id == student.class_id,
                Notice.class_id.is_(None),
            ),
            or_(
                Notice.target_user_id.is_(None),
                Notice.target_user_id == current_user.id,
                Notice.target_user_id == student_user_id,
            ),
        )
        .order_by(Notice.created_at.desc())
        .limit(30)
        .all()
    )
    return [
        MiniNoticeItem(
            title=row.title,
            content=row.content,
            notice_type=row.notice_type,
            created_at=row.created_at,
        )
        for row in rows
    ]
