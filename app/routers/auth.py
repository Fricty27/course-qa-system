from fastapi import APIRouter, HTTPException, Header, Depends
from app.models import LoginRequest, RegisterRequest, ProfileUpdate, PasswordChange, BasicInfoUpdate
from app.services import database as db

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的认证头格式")
    token = authorization[7:]
    user = db.get_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Token 无效或已过期，请重新登录")
    return user


def require_teacher(authorization: str = Header(...)):
    user = get_current_user(authorization)
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可执行此操作")
    return user


@router.post("/register", summary="注册")
def register(req: RegisterRequest):
    if req.role not in ("teacher", "student"):
        raise HTTPException(status_code=400, detail="role 必须是 teacher 或 student")
    if db.get_user_by_username(req.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="密码至少4位")
    user_id = db.create_user(req.username, req.password, req.role)
    return {"status": "ok", "user_id": user_id, "role": req.role}


@router.post("/login", summary="登录")
def login(req: LoginRequest):
    user = db.get_user_by_username(req.username)
    if user is None or not db.verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = db.create_session(user["id"])
    return {"token": token, "role": user["role"], "username": user["username"]}


@router.get("/me", summary="获取当前用户信息")
def me(authorization: str = Header(...)):
    user = get_current_user(authorization)
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "avatar": user["avatar"],
        "nickname": user["nickname"],
        "gender": user["gender"],
        "phone": user["phone"],
    }


@router.put("/profile", summary="更新头像和昵称")
def update_profile(body: ProfileUpdate, user=Depends(get_current_user)):
    db.update_user_profile(user["id"], body.avatar, body.nickname)
    return {"status": "ok"}


@router.put("/basic-info", summary="更新基本资料（性别、手机号）")
def update_basic_info(body: BasicInfoUpdate, user=Depends(get_current_user)):
    db.update_user_basic_info(user["id"], body.gender, body.phone)
    return {"status": "ok"}


@router.put("/password", summary="修改密码")
def change_password(body: PasswordChange, user=Depends(get_current_user)):
    full_user = db.get_user_by_username(user["username"])
    if not db.verify_password(body.current_password, full_user["password_hash"]):
        raise HTTPException(status_code=400, detail="当前密码错误")
    if len(body.new_password) < 4:
        raise HTTPException(status_code=400, detail="新密码至少4位")
    db.change_password(user["id"], body.new_password)
    return {"status": "ok"}


@router.delete("/account", summary="注销账号")
def delete_account(user=Depends(get_current_user)):
    db.delete_user(user["id"], user["role"])
    return {"status": "ok"}


@router.get("/users/{user_id}/profile", summary="查看用户公开资料")
def get_user_profile(user_id: int, user=Depends(get_current_user)):
    row = db.get_user_public_profile(user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return dict(row)
