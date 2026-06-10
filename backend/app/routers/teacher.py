from __future__ import annotations

import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_roles
from app.models import (
    BehaviorRecord,
    ClassRoom,
    Exam,
    Notice,
    ParentStudentRelation,
    QuestionBankResource,
    QuestionStatus,
    Score,
    StudentProfile,
    User,
    UserRole,
)
from app.schemas import (
    BehaviorCreate,
    BehaviorResponse,
    ClassAverageItem,
    ClassRoomResponse,
    ExamCreate,
    ExamResponse,
    MessageResponse,
    NoticeCreate,
    NoticeResponse,
    QuestionResourceResponse,
    ScoreBatchUpsert,
    ScoreResponse,
    StudentResponse,
    StudentUpdate,
    SubjectBalanceItem,
    TrendItem,
)
from app.services import audit_log


router = APIRouter(prefix="/api/teacher", tags=["Teacher"])

PERM_STUDENT_WRITE = "student:write"
PERM_SCORE_WRITE = "score:write"
PERM_NOTICE_WRITE = "notice:write"
PERM_ANALYSIS_VIEW = "analysis:view"
PERM_QUESTION_BANK_VIEW = "question_bank:view"


def require_teacher_permissions(*permissions: str):
    def checker(current_user: User = Depends(require_roles(UserRole.TEACHER, UserRole.ADMIN))) -> User:
        if current_user.role == UserRole.ADMIN:
            return current_user

        current_permissions = set(current_user.permissions or [])
        if permissions and not any(item in current_permissions for item in permissions):
            required = " / ".join(permissions)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"权限不足，需具备权限：{required}")
        return current_user

    return checker


def _build_student_response(student: StudentProfile) -> StudentResponse:
    return StudentResponse(
        id=student.id,
        user_id=student.user.id,
        student_no=student.student_no,
        full_name=student.user.full_name,
        gender=student.gender,
        class_id=student.class_id,
        class_name=student.class_room.name,
        grade=student.class_room.grade,
        enrollment_year=student.enrollment_year,
        address=student.address,
        guardian_note=student.guardian_note,
    )


@router.get("/classes", response_model=list[ClassRoomResponse])
def list_classes(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_teacher_permissions(PERM_STUDENT_WRITE, PERM_SCORE_WRITE, PERM_NOTICE_WRITE, PERM_ANALYSIS_VIEW)
    ),
) -> list[ClassRoomResponse]:
    classes = db.query(ClassRoom).order_by(ClassRoom.grade.asc(), ClassRoom.name.asc()).all()
    return [ClassRoomResponse.model_validate(item, from_attributes=True) for item in classes]


@router.get("/students", response_model=list[StudentResponse])
def list_students(
    class_id: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_teacher_permissions(PERM_STUDENT_WRITE, PERM_SCORE_WRITE, PERM_NOTICE_WRITE, PERM_ANALYSIS_VIEW)
    ),
) -> list[StudentResponse]:
    query = db.query(StudentProfile).join(User, User.id == StudentProfile.user_id).join(ClassRoom, ClassRoom.id == StudentProfile.class_id)
    if class_id:
        query = query.filter(StudentProfile.class_id == class_id)
    if keyword:
        query = query.filter(
            (StudentProfile.student_no.like(f"%{keyword}%"))
            | (User.full_name.like(f"%{keyword}%"))
        )
    students = query.order_by(StudentProfile.id.asc()).all()
    return [_build_student_response(student) for student in students]


@router.put("/students/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_STUDENT_WRITE)),
) -> StudentResponse:
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生不存在")

    class_room = db.query(ClassRoom).filter(ClassRoom.id == payload.class_id).first()
    if class_room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")

    student.user.full_name = payload.full_name
    student.gender = payload.gender
    student.birth_date = payload.birth_date
    student.enrollment_year = payload.enrollment_year
    student.address = payload.address
    student.guardian_note = payload.guardian_note
    student.class_id = payload.class_id

    db.commit()
    db.refresh(student)
    audit_log(db, current_user.id, "student", "update", f"student {student.student_no}")
    return _build_student_response(student)


@router.get("/students/{student_id}/behaviors", response_model=list[BehaviorResponse])
def list_behaviors(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_STUDENT_WRITE)),
) -> list[BehaviorResponse]:
    rows = (
        db.query(BehaviorRecord)
        .filter(BehaviorRecord.student_id == student_id)
        .order_by(BehaviorRecord.record_date.desc(), BehaviorRecord.id.desc())
        .all()
    )
    return [
        BehaviorResponse(
            id=row.id,
            student_id=row.student_id,
            student_name=row.student.user.full_name,
            category=row.category,
            title=row.title,
            description=row.description,
            score_delta=row.score_delta,
            record_date=row.record_date,
            teacher_name=row.teacher.full_name,
        )
        for row in rows
    ]


@router.post("/behaviors", response_model=BehaviorResponse)
def create_behavior(
    payload: BehaviorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_STUDENT_WRITE)),
) -> BehaviorResponse:
    student = db.query(StudentProfile).filter(StudentProfile.id == payload.student_id).first()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生不存在")

    row = BehaviorRecord(
        student_id=payload.student_id,
        teacher_id=current_user.id,
        category=payload.category,
        title=payload.title,
        description=payload.description,
        score_delta=payload.score_delta,
        record_date=payload.record_date,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    audit_log(db, current_user.id, "behavior", "create", f"student {student.student_no}")
    return BehaviorResponse(
        id=row.id,
        student_id=row.student_id,
        student_name=student.user.full_name,
        category=row.category,
        title=row.title,
        description=row.description,
        score_delta=row.score_delta,
        record_date=row.record_date,
        teacher_name=current_user.full_name,
    )


@router.get("/exams", response_model=list[ExamResponse])
def list_exams(
    class_id: int | None = Query(default=None),
    subject: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_SCORE_WRITE)),
) -> list[ExamResponse]:
    query = db.query(Exam)
    if class_id:
        query = query.filter(Exam.class_id == class_id)
    if subject:
        query = query.filter(Exam.subject == subject)
    rows = query.order_by(Exam.exam_date.desc(), Exam.id.desc()).all()
    return [
        ExamResponse(
            id=row.id,
            name=row.name,
            exam_type=row.exam_type,
            subject=row.subject,
            grade=row.grade,
            class_id=row.class_id,
            class_name=row.class_room.name,
            exam_date=row.exam_date,
            is_published=row.is_published,
        )
        for row in rows
    ]


@router.post("/exams", response_model=ExamResponse)
def create_exam(
    payload: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_SCORE_WRITE)),
) -> ExamResponse:
    class_room = db.query(ClassRoom).filter(ClassRoom.id == payload.class_id).first()
    if class_room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="班级不存在")

    exam = Exam(
        name=payload.name,
        exam_type=payload.exam_type,
        subject=payload.subject,
        grade=payload.grade,
        class_id=payload.class_id,
        exam_date=payload.exam_date,
        creator_id=current_user.id,
        is_published=False,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    audit_log(db, current_user.id, "exam", "create", f"exam {exam.id}")
    return ExamResponse(
        id=exam.id,
        name=exam.name,
        exam_type=exam.exam_type,
        subject=exam.subject,
        grade=exam.grade,
        class_id=exam.class_id,
        class_name=class_room.name,
        exam_date=exam.exam_date,
        is_published=exam.is_published,
    )


@router.post("/exams/{exam_id}/scores", response_model=MessageResponse)
def upsert_scores(
    exam_id: int,
    payload: ScoreBatchUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_SCORE_WRITE)),
) -> MessageResponse:
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考试不存在")

    student_ids = {item.student_id for item in payload.scores}
    students = db.query(StudentProfile).filter(StudentProfile.id.in_(student_ids)).all() if student_ids else []
    if len(students) != len(student_ids):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="存在无效学生 ID")

    for item in payload.scores:
        score = db.query(Score).filter(Score.exam_id == exam_id, Score.student_id == item.student_id).first()
        if score is None:
            score = Score(exam_id=exam_id, student_id=item.student_id, score=item.score, comment=item.comment)
            db.add(score)
        else:
            score.score = item.score
            score.comment = item.comment

    exam.is_published = False
    db.commit()
    audit_log(db, current_user.id, "score", "upsert", f"exam {exam_id}")
    return MessageResponse(message="成绩保存成功")


@router.get("/exams/{exam_id}/scores", response_model=list[ScoreResponse])
def list_scores(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_SCORE_WRITE)),
) -> list[ScoreResponse]:
    rows = (
        db.query(Score)
        .filter(Score.exam_id == exam_id)
        .order_by(Score.rank.is_(None).asc(), Score.rank.asc(), Score.score.desc())
        .all()
    )
    return [
        ScoreResponse(
            id=row.id,
            exam_id=row.exam_id,
            student_id=row.student_id,
            student_name=row.student.user.full_name,
            score=row.score,
            rank=row.rank,
            comment=row.comment,
        )
        for row in rows
    ]


@router.post("/exams/{exam_id}/publish", response_model=MessageResponse)
def publish_exam_scores(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_SCORE_WRITE)),
) -> MessageResponse:
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if exam is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="考试不存在")

    rows = db.query(Score).filter(Score.exam_id == exam_id).order_by(Score.score.desc()).all()
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="暂无成绩可发布")

    current_rank = 1
    previous_score = None
    for index, row in enumerate(rows, start=1):
        if previous_score is not None and row.score != previous_score:
            current_rank = index
        row.rank = current_rank
        previous_score = row.score

    exam.is_published = True
    db.commit()
    audit_log(db, current_user.id, "score", "publish", f"exam {exam_id}")
    return MessageResponse(message="成绩发布成功")


@router.get("/notices", response_model=list[NoticeResponse])
def list_notices(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_NOTICE_WRITE)),
) -> list[NoticeResponse]:
    rows = db.query(Notice).order_by(Notice.created_at.desc()).all()
    return [
        NoticeResponse(
            id=row.id,
            title=row.title,
            content=row.content,
            notice_type=row.notice_type,
            class_id=row.class_id,
            target_user_id=row.target_user_id,
            publisher_name=row.publisher.full_name,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/notices", response_model=NoticeResponse)
def create_notice(
    payload: NoticeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_NOTICE_WRITE)),
) -> NoticeResponse:
    if payload.notice_type.name == "CLASS" and payload.class_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="班级通知需指定班级")
    if payload.notice_type.name == "PERSONAL" and payload.target_user_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="个人消息需指定目标用户")

    row = Notice(
        title=payload.title,
        content=payload.content,
        notice_type=payload.notice_type,
        publisher_id=current_user.id,
        class_id=payload.class_id,
        target_user_id=payload.target_user_id,
        is_published=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    audit_log(db, current_user.id, "notice", "create", f"notice {row.id}")
    return NoticeResponse(
        id=row.id,
        title=row.title,
        content=row.content,
        notice_type=row.notice_type,
        class_id=row.class_id,
        target_user_id=row.target_user_id,
        publisher_name=current_user.full_name,
        created_at=row.created_at,
    )


@router.get("/analytics/class-average", response_model=list[ClassAverageItem])
def analytics_class_average(
    class_id: int | None = Query(default=None),
    subject: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_ANALYSIS_VIEW)),
) -> list[ClassAverageItem]:
    query = (
        db.query(Exam.subject, func.avg(Score.score).label("avg_score"))
        .join(Score, Score.exam_id == Exam.id)
        .filter(Exam.is_published.is_(True))
    )
    if class_id:
        query = query.filter(Exam.class_id == class_id)
    if subject:
        query = query.filter(Exam.subject == subject)
    rows = query.group_by(Exam.subject).order_by(Exam.subject.asc()).all()
    return [ClassAverageItem(subject=row.subject, average_score=float(row.avg_score or 0)) for row in rows]


@router.get("/analytics/ranking-trend", response_model=list[TrendItem])
def analytics_ranking_trend(
    student_id: int,
    subject: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_ANALYSIS_VIEW)),
) -> list[TrendItem]:
    query = (
        db.query(Score, Exam)
        .join(Exam, Exam.id == Score.exam_id)
        .filter(Score.student_id == student_id, Exam.is_published.is_(True))
    )
    if subject:
        query = query.filter(Exam.subject == subject)
    rows = query.order_by(Exam.exam_date.asc()).all()
    return [
        TrendItem(
            exam_name=exam.name,
            exam_date=exam.exam_date,
            score=float(score.score),
            rank=score.rank,
        )
        for score, exam in rows
    ]


@router.get("/analytics/score-fluctuation", response_model=list[TrendItem])
def analytics_score_fluctuation(
    student_id: int,
    subject: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_ANALYSIS_VIEW)),
) -> list[TrendItem]:
    rows = (
        db.query(Score, Exam)
        .join(Exam, Exam.id == Score.exam_id)
        .filter(Score.student_id == student_id, Exam.subject == subject, Exam.is_published.is_(True))
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


@router.get("/analytics/subject-balance", response_model=list[SubjectBalanceItem])
def analytics_subject_balance(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_ANALYSIS_VIEW)),
) -> list[SubjectBalanceItem]:
    rows = (
        db.query(Score, Exam)
        .join(Exam, Exam.id == Score.exam_id)
        .filter(Score.student_id == student_id, Exam.is_published.is_(True))
        .order_by(Exam.subject.asc(), desc(Exam.exam_date))
        .all()
    )
    latest_by_subject: dict[str, SubjectBalanceItem] = {}
    for score, exam in rows:
        if exam.subject not in latest_by_subject:
            latest_by_subject[exam.subject] = SubjectBalanceItem(subject=exam.subject, score=float(score.score))
    return list(latest_by_subject.values())


@router.get("/analytics/export")
def export_scores(
    class_id: int | None = Query(default=None),
    subject: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_ANALYSIS_VIEW)),
) -> StreamingResponse:
    query = (
        db.query(Score, Exam, StudentProfile, User)
        .join(Exam, Exam.id == Score.exam_id)
        .join(StudentProfile, StudentProfile.id == Score.student_id)
        .join(User, User.id == StudentProfile.user_id)
        .filter(Exam.is_published.is_(True))
    )
    if class_id:
        query = query.filter(Exam.class_id == class_id)
    if subject:
        query = query.filter(Exam.subject == subject)
    rows = query.order_by(Exam.exam_date.desc()).all()

    content = StringIO()
    writer = csv.writer(content)
    writer.writerow(["exam_name", "subject", "student_no", "student_name", "score", "rank", "exam_date"])
    for score, exam, student, user in rows:
        writer.writerow([exam.name, exam.subject, student.student_no, user.full_name, score.score, score.rank, exam.exam_date])

    output = StringIO(content.getvalue())
    headers = {"Content-Disposition": "attachment; filename=scores_export.csv"}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)


@router.get("/analytics/print-report")
def print_report(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_ANALYSIS_VIEW)),
) -> dict:
    student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学生不存在")

    latest_scores = (
        db.query(Score, Exam)
        .join(Exam, Exam.id == Score.exam_id)
        .filter(Score.student_id == student_id, Exam.is_published.is_(True))
        .order_by(Exam.exam_date.desc())
        .limit(10)
        .all()
    )
    behaviors = (
        db.query(BehaviorRecord)
        .filter(BehaviorRecord.student_id == student_id)
        .order_by(BehaviorRecord.record_date.desc())
        .limit(10)
        .all()
    )

    return {
        "student": {
            "name": student.user.full_name,
            "student_no": student.student_no,
            "class_name": student.class_room.name,
            "grade": student.class_room.grade,
        },
        "scores": [
            {
                "exam_name": exam.name,
                "subject": exam.subject,
                "exam_date": exam.exam_date,
                "score": float(score.score),
                "rank": score.rank,
            }
            for score, exam in latest_scores
        ],
        "behaviors": [
            {
                "category": behavior.category,
                "title": behavior.title,
                "description": behavior.description,
                "record_date": behavior.record_date,
                "score_delta": behavior.score_delta,
            }
            for behavior in behaviors
        ],
    }


@router.get("/question-bank/search", response_model=list[QuestionResourceResponse])
def search_question_bank(
    keyword: str | None = Query(default=None),
    subject: str | None = Query(default=None),
    grade: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_QUESTION_BANK_VIEW)),
) -> list[QuestionResourceResponse]:
    query = db.query(QuestionBankResource).filter(QuestionBankResource.status == QuestionStatus.ACTIVE)
    if keyword:
        query = query.filter(QuestionBankResource.title.like(f"%{keyword}%"))
    if subject:
        query = query.filter(QuestionBankResource.subject == subject)
    if grade:
        query = query.filter(QuestionBankResource.grade == grade)
    rows = query.order_by(QuestionBankResource.created_at.desc()).all()
    return [QuestionResourceResponse.model_validate(row, from_attributes=True) for row in rows]


@router.get("/parents/{student_id}")
def list_parents_for_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher_permissions(PERM_STUDENT_WRITE)),
) -> list[dict]:
    rows = db.query(ParentStudentRelation).filter(ParentStudentRelation.student_id == student_id).all()
    return [
        {
            "parent_id": row.parent_id,
            "parent_name": row.parent.full_name,
            "mobile": row.parent.mobile,
            "relation": row.relation_label,
        }
        for row in rows
    ]
