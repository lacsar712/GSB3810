from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import (
    BehaviorCategory,
    BehaviorRecord,
    ClassRoom,
    DataDictionary,
    Exam,
    Notice,
    NoticeType,
    ParentStudentRelation,
    QuestionBankResource,
    QuestionStatus,
    Score,
    StudentProfile,
    SystemConfig,
    User,
    UserRole,
)
from app.security import hash_password


def _create_user(
    db: Session,
    username: str,
    password: str,
    role: UserRole,
    full_name: str,
    mobile: str,
    permissions: list[str] | None = None,
) -> User:
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user

    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        full_name=full_name,
        mobile=mobile,
        permissions=permissions or [],
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def seed_initial_data(db: Session) -> None:
    existed = db.query(User).filter(User.role == UserRole.ADMIN).first()
    if existed:
        return

    admin = _create_user(
        db,
        username="sys_admin",
        password="Admin@123456",
        role=UserRole.ADMIN,
        full_name="系统管理员",
        mobile="13800000000",
        permissions=["teacher:manage", "question_bank:manage", "system:manage", "backup:manage"],
    )

    teacher_1 = _create_user(
        db,
        username="teacher_zhang",
        password="Teacher@123456",
        role=UserRole.TEACHER,
        full_name="张老师",
        mobile="13800000001",
        permissions=[
            "student:write",
            "score:write",
            "notice:write",
            "analysis:view",
            "question_bank:view",
        ],
    )
    teacher_2 = _create_user(
        db,
        username="teacher_liu",
        password="Teacher@123456",
        role=UserRole.TEACHER,
        full_name="刘老师",
        mobile="13800000002",
        permissions=["student:write", "score:write", "notice:write", "analysis:view"],
    )

    class_1 = ClassRoom(name="高一(1)班", grade="高一", academic_year="2025-2026", homeroom_teacher_id=teacher_1.id)
    class_2 = ClassRoom(name="高一(2)班", grade="高一", academic_year="2025-2026", homeroom_teacher_id=teacher_2.id)
    db.add_all([class_1, class_2])
    db.flush()

    stu_user_1 = _create_user(
        db,
        username="stu_sun",
        password="Student@123456",
        role=UserRole.STUDENT,
        full_name="孙晨",
        mobile="13900000001",
    )
    stu_user_2 = _create_user(
        db,
        username="stu_lin",
        password="Student@123456",
        role=UserRole.STUDENT,
        full_name="林悦",
        mobile="13900000002",
    )
    stu_user_3 = _create_user(
        db,
        username="stu_he",
        password="Student@123456",
        role=UserRole.STUDENT,
        full_name="何杰",
        mobile="13900000003",
    )

    student_1 = StudentProfile(
        user_id=stu_user_1.id,
        student_no="S2025001",
        class_id=class_1.id,
        gender="男",
        birth_date=date(2010, 5, 4),
        enrollment_year=2025,
        address="上海市浦东新区",
        guardian_note="对理科兴趣浓厚",
    )
    student_2 = StudentProfile(
        user_id=stu_user_2.id,
        student_no="S2025002",
        class_id=class_1.id,
        gender="女",
        birth_date=date(2010, 8, 19),
        enrollment_year=2025,
        address="上海市闵行区",
        guardian_note="英语阅读能力突出",
    )
    student_3 = StudentProfile(
        user_id=stu_user_3.id,
        student_no="S2025003",
        class_id=class_2.id,
        gender="男",
        birth_date=date(2010, 2, 12),
        enrollment_year=2025,
        address="上海市徐汇区",
        guardian_note="需加强时间管理",
    )
    db.add_all([student_1, student_2, student_3])
    db.flush()

    parent_1 = _create_user(
        db,
        username="parent_sun",
        password="Parent@123456",
        role=UserRole.PARENT,
        full_name="孙晨家长",
        mobile="13700000001",
    )
    parent_2 = _create_user(
        db,
        username="parent_lin",
        password="Parent@123456",
        role=UserRole.PARENT,
        full_name="林悦家长",
        mobile="13700000002",
    )
    parent_3 = _create_user(
        db,
        username="parent_he",
        password="Parent@123456",
        role=UserRole.PARENT,
        full_name="何杰家长",
        mobile="13700000003",
    )

    db.add_all(
        [
            ParentStudentRelation(parent_id=parent_1.id, student_id=student_1.id, relation_label="父亲"),
            ParentStudentRelation(parent_id=parent_2.id, student_id=student_2.id, relation_label="母亲"),
            ParentStudentRelation(parent_id=parent_3.id, student_id=student_3.id, relation_label="父亲"),
        ]
    )

    exams = [
        Exam(
            name="高一第一次月考",
            exam_type="MONTHLY",
            subject="数学",
            grade="高一",
            class_id=class_1.id,
            exam_date=date(2025, 9, 20),
            is_published=True,
            creator_id=teacher_1.id,
        ),
        Exam(
            name="高一第二次月考",
            exam_type="MONTHLY",
            subject="数学",
            grade="高一",
            class_id=class_1.id,
            exam_date=date(2025, 11, 2),
            is_published=True,
            creator_id=teacher_1.id,
        ),
        Exam(
            name="高一期末考试",
            exam_type="FINAL",
            subject="数学",
            grade="高一",
            class_id=class_1.id,
            exam_date=date(2026, 1, 16),
            is_published=True,
            creator_id=teacher_1.id,
        ),
        Exam(
            name="高一期末考试",
            exam_type="FINAL",
            subject="语文",
            grade="高一",
            class_id=class_1.id,
            exam_date=date(2026, 1, 16),
            is_published=True,
            creator_id=teacher_1.id,
        ),
        Exam(
            name="高一期末考试",
            exam_type="FINAL",
            subject="英语",
            grade="高一",
            class_id=class_1.id,
            exam_date=date(2026, 1, 16),
            is_published=True,
            creator_id=teacher_1.id,
        ),
    ]
    db.add_all(exams)
    db.flush()

    db.add_all(
        [
            Score(exam_id=exams[0].id, student_id=student_1.id, score=Decimal("86.00"), rank=2),
            Score(exam_id=exams[0].id, student_id=student_2.id, score=Decimal("91.00"), rank=1),
            Score(exam_id=exams[1].id, student_id=student_1.id, score=Decimal("90.00"), rank=1),
            Score(exam_id=exams[1].id, student_id=student_2.id, score=Decimal("88.00"), rank=2),
            Score(exam_id=exams[2].id, student_id=student_1.id, score=Decimal("93.00"), rank=1),
            Score(exam_id=exams[2].id, student_id=student_2.id, score=Decimal("89.00"), rank=2),
            Score(exam_id=exams[3].id, student_id=student_1.id, score=Decimal("87.00"), rank=2),
            Score(exam_id=exams[3].id, student_id=student_2.id, score=Decimal("92.00"), rank=1),
            Score(exam_id=exams[4].id, student_id=student_1.id, score=Decimal("88.00"), rank=2),
            Score(exam_id=exams[4].id, student_id=student_2.id, score=Decimal("94.00"), rank=1),
        ]
    )

    db.add_all(
        [
            BehaviorRecord(
                student_id=student_1.id,
                teacher_id=teacher_1.id,
                category=BehaviorCategory.REWARD,
                title="课堂发言积极",
                description="主动分享解题思路，帮助同学理解重难点。",
                score_delta=3,
                record_date=date(2026, 2, 10),
            ),
            BehaviorRecord(
                student_id=student_1.id,
                teacher_id=teacher_1.id,
                category=BehaviorCategory.OBSERVATION,
                title="作业质量稳定",
                description="近三周数学作业正确率维持在90%以上。",
                score_delta=1,
                record_date=date(2026, 2, 20),
            ),
            BehaviorRecord(
                student_id=student_2.id,
                teacher_id=teacher_1.id,
                category=BehaviorCategory.REWARD,
                title="英语竞赛获奖",
                description="校级英语演讲比赛二等奖。",
                score_delta=5,
                record_date=date(2026, 2, 14),
            ),
        ]
    )

    db.add_all(
        [
            Notice(
                title="期中复习安排",
                content="本周三下午组织数学与英语联合答疑，请同学提前准备问题清单。",
                notice_type=NoticeType.CLASS,
                publisher_id=teacher_1.id,
                class_id=class_1.id,
                target_user_id=None,
                is_published=True,
            ),
            Notice(
                title="心理健康讲座通知",
                content="周五第七节课在报告厅开展心理健康专题讲座，请准时参加。",
                notice_type=NoticeType.ANNOUNCEMENT,
                publisher_id=teacher_2.id,
                class_id=None,
                target_user_id=None,
                is_published=True,
            ),
            Notice(
                title="学习资料推送",
                content="已上传高一数学函数专题习题，请在周日前完成。",
                notice_type=NoticeType.RESOURCE,
                publisher_id=teacher_1.id,
                class_id=class_1.id,
                target_user_id=None,
                is_published=True,
            ),
        ]
    )

    db.add_all(
        [
            QuestionBankResource(
                title="函数与导数专题训练",
                subject="数学",
                grade="高一",
                tags="函数,导数,压轴题",
                description="覆盖函数综合题与导数基础题，附参考答案。",
                resource_url="https://example.com/resources/math-function.pdf",
                status=QuestionStatus.ACTIVE,
                publisher_id=admin.id,
            ),
            QuestionBankResource(
                title="高一英语阅读理解分层训练",
                subject="英语",
                grade="高一",
                tags="阅读,完形,词汇",
                description="按难度分层，适用于周测与课后巩固。",
                resource_url="https://example.com/resources/english-reading.pdf",
                status=QuestionStatus.ACTIVE,
                publisher_id=admin.id,
            ),
        ]
    )

    db.add_all(
        [
            SystemConfig(
                config_key="school_name",
                config_value="星河高级中学",
                description="学校名称",
                updated_by=admin.id,
            ),
            SystemConfig(
                config_key="score_publish_mode",
                config_value="manual",
                description="成绩发布模式",
                updated_by=admin.id,
            ),
            SystemConfig(
                config_key="backup_retention_days",
                config_value="30",
                description="备份保留天数",
                updated_by=admin.id,
            ),
        ]
    )

    db.add_all(
        [
            DataDictionary(dict_type="exam_type", dict_key="MONTHLY", dict_value="月考", sort_order=1),
            DataDictionary(dict_type="exam_type", dict_key="MIDTERM", dict_value="期中", sort_order=2),
            DataDictionary(dict_type="exam_type", dict_key="FINAL", dict_value="期末", sort_order=3),
            DataDictionary(dict_type="notice_type", dict_key="CLASS", dict_value="班级通知", sort_order=1),
            DataDictionary(dict_type="notice_type", dict_key="PERSONAL", dict_value="个人消息", sort_order=2),
            DataDictionary(dict_type="notice_type", dict_key="RESOURCE", dict_value="学习资料", sort_order=3),
        ]
    )

    db.commit()
