from fastapi import APIRouter, Depends, HTTPException
from app.routers.auth import require_teacher, get_current_user
from app.services import database as db

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("/student/{course_key}", summary="学生查看自己在某课程的提问记录")
def get_my_history(course_key: str, user=Depends(get_current_user)):
    rows = db.get_student_question_logs(course_key, user["id"])
    return [dict(r) for r in rows]


@router.delete("/log/{log_id}", summary="删除一条提问记录")
def delete_log(log_id: int, user=Depends(get_current_user)):
    ok = db.delete_question_log(log_id, user["id"], user["role"])
    if not ok:
        raise HTTPException(status_code=404, detail="记录不存在或无权限删除")
    return {"status": "ok"}


@router.get("/{course_key}", summary="教师查看课程全部提问记录")
def get_history(course_key: str, teacher=Depends(require_teacher)):
    rows = db.get_question_logs(course_key, teacher["id"])
    return [dict(r) for r in rows]
