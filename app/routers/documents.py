import os
import glob as glob_mod
from fastapi import APIRouter, HTTPException, Depends
from app.routers.auth import require_teacher, get_current_user
from app.services import database as db
from app.services.vector_store import delete_chunks_by_doc

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/{course_key}/student", summary="查看课程文档列表（学生）")
def list_documents_student(course_key: str, user=Depends(get_current_user)):
    course = db.get_course_by_key(course_key)
    if course is None:
        raise HTTPException(status_code=404, detail="课程不存在")
    files = sorted(glob_mod.glob(f"data/uploads/{course_key}_*"))
    return [
        {
            "filename": os.path.basename(f),
            "display_name": os.path.basename(f)[len(course_key) + 1:],
            "size": os.path.getsize(f),
        }
        for f in files
    ]


@router.get("/{course_key}", summary="查看课程已上传文档（教师）")
def list_documents(course_key: str, teacher=Depends(require_teacher)):
    course = db.get_course_by_key(course_key)
    if course is None or course["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=403, detail="无权限")
    files = sorted(glob_mod.glob(f"data/uploads/{course_key}_*"))
    return [
        {
            "filename": os.path.basename(f),
            "display_name": os.path.basename(f)[len(course_key) + 1:],
            "size": os.path.getsize(f),
        }
        for f in files
    ]


@router.delete("/{course_key}", summary="删除课程文档（教师）")
def delete_document(course_key: str, filename: str, teacher=Depends(require_teacher)):
    # filename 作为查询参数传入，格式为 {course_key}_{原始文件名}
    course = db.get_course_by_key(course_key)
    if course is None or course["teacher_id"] != teacher["id"]:
        raise HTTPException(status_code=403, detail="无权限")
    if not filename.startswith(f"{course_key}_"):
        raise HTTPException(status_code=400, detail="文件不属于该课程")
    delete_chunks_by_doc(course_key, filename)
    file_path = f"data/uploads/{filename}"
    if os.path.exists(file_path):
        os.remove(file_path)
    return {"status": "ok"}
