from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models import ParentStudentRelation, StudentProfile, User, UserRole
from app.schemas import AuthTokenResponse, LoginRequest, UserBrief, WechatLoginRequest
from app.security import create_access_token, fake_wechat_openid, verify_password


router = APIRouter(prefix="/api/auth", tags=["Auth"])

ROLE_MAP = {
    "STUDENT": UserRole.STUDENT,
    "学生": UserRole.STUDENT,
    "PARENT": UserRole.PARENT,
    "家长": UserRole.PARENT,
}


def _normalize_mini_role(raw_role: str) -> UserRole:
    normalized = raw_role.strip()
    role = ROLE_MAP.get(normalized.upper()) or ROLE_MAP.get(normalized)
    if role is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="角色仅支持 STUDENT 或 PARENT")
    return role


@router.post("/web-login", response_model=AuthTokenResponse)
def web_login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")

    if user.role not in {UserRole.ADMIN, UserRole.TEACHER}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该角色不允许网页登录")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")

    token = create_access_token(user.id, user.role.value)
    return AuthTokenResponse(access_token=token, user=UserBrief.model_validate(user))


@router.post("/wechat-login", response_model=AuthTokenResponse)
def wechat_login(payload: WechatLoginRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
    role = _normalize_mini_role(payload.role)

    student_no = (payload.student_no or "").strip()
    if not student_no:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="请提供学号用于身份绑定")

    openid = fake_wechat_openid(payload.code.strip())
    student = db.query(StudentProfile).filter(StudentProfile.student_no == student_no).first()
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到对应学生档案")

    if role == UserRole.STUDENT:
        user = db.query(User).filter(User.id == student.user_id, User.role == UserRole.STUDENT).first()
    else:
        relation = (
            db.query(ParentStudentRelation)
            .filter(ParentStudentRelation.student_id == student.id)
            .order_by(ParentStudentRelation.id.asc())
            .first()
        )
        if relation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该学生暂未绑定家长")
        user = db.query(User).filter(User.id == relation.parent_id, User.role == UserRole.PARENT).first()

    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号不可用")

    existing = db.query(User).filter(User.wechat_openid == openid, User.id != user.id).first()
    if existing:
        existing.wechat_openid = None

    user.wechat_openid = openid
    db.commit()

    token = create_access_token(user.id, role.value)
    return AuthTokenResponse(access_token=token, user=UserBrief.model_validate(user))


@router.get("/me", response_model=UserBrief)
def get_me(current_user: User = Depends(get_current_user)) -> UserBrief:
    return UserBrief.model_validate(current_user)
