import os
import glob as glob_mod
from fastapi import APIRouter, HTTPException, Depends
from app.models import CourseCreate, CourseRename
from app.routers.auth import require_teacher, get_current_user
from app.services import database as db
from app.services.vector_store import delete_collection

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.post("/", summary="创建课程（教师）")
def create_course(body: CourseCreate, teacher=Depends(require_teacher)):
    if not body.course_key.strip():
        raise HTTPException(status_code=400, detail="课程码不能为空")
    if db.get_course_by_key(body.course_key):
        raise HTTPException(status_code=400, detail="课程码已被使用，请换一个")
    course_id = db.create_course(body.name, body.course_key, teacher["id"])
    group_id = db.create_group(body.name, body.course_key)
    db.add_group_member(group_id, teacher["id"])
    return {"status": "ok", "course_id": course_id, "course_key": body.course_key}


@router.get("/", summary="查看我的课程列表（教师）")
def list_courses(teacher=Depends(require_teacher)):
    rows = db.get_courses_by_teacher(teacher["id"])
    return [dict(r) for r in rows]


@router.get("/mine", summary="学生查看已加入的课程")
def my_courses(user=Depends(get_current_user)):
    if user["role"] != "student":
        raise HTTPException(status_code=403, detail="仅学生可用")
    rows = db.get_student_courses(user["id"])
    return [dict(r) for r in rows]


@router.patch("/{course_key}", summary="修改课程名（教师）")
def rename_course(course_key: str, body: CourseRename, teacher=Depends(require_teacher)):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="课程名不能为空")
    ok = db.update_course_name(course_key, teacher["id"], body.name.strip())
    if not ok:
        raise HTTPException(status_code=404, detail="课程不存在或无权限")
    return {"status": "ok"}


@router.delete("/{course_key}", summary="删除课程（教师）")
def remove_course(course_key: str, teacher=Depends(require_teacher)):
    ok = db.delete_course(course_key, teacher["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="课程不存在或无权限")
    delete_collection(course_key)
    for f in glob_mod.glob(f"data/uploads/{course_key}_*"):
        try:
            os.remove(f)
        except OSError:
            pass
    return {"status": "ok"}


@router.post("/{course_key}/join", summary="学生加入课程（记录成员）")
def join_course(course_key: str, user=Depends(get_current_user)):
    course = db.get_course_by_key(course_key)
    if course is None:
        raise HTTPException(status_code=404, detail="课程不存在")
    if user["role"] != "student":
        raise HTTPException(status_code=400, detail="仅学生可加入课程")
    db.add_course_member(user["id"], course_key)
    group = db.get_group_by_course_key(course_key)
    if group:
        db.add_group_member(group["id"], user["id"])
    return {"status": "ok"}


@router.get("/{course_key}/students", summary="查看课程学生成员（教师）")
def get_students(course_key: str, teacher=Depends(require_teacher)):
    course = db.get_course_by_key(course_key)
    if course is None or course["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=403, detail="无权限")
    members = db.get_course_members(course_key)
    return [dict(m) for m in members]


@router.get("/{course_key}", summary="验证课程是否存在（学生用，无需登录）")
def check_course(course_key: str):
    course = db.get_course_by_key(course_key)
    if course is None:
        raise HTTPException(status_code=404, detail="课程码不存在，请确认后重试")
    return {
        "name": course["name"],
        "course_key": course["course_key"],
        "teacher_id": course["teacher_id"],
        "teacher_username": course["teacher_username"],
        "teacher_nickname": course["teacher_nickname"],
    }
