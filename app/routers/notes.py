from fastapi import APIRouter, Depends, HTTPException
from app.models import NoteCreate, NoteUpdate, NoteCommentCreate
from app.routers.auth import get_current_user
from app.services import database as db

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.get("/public", summary="教师查看其课程下的公开笔记")
def get_public_notes(user=Depends(get_current_user)):
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可访问")
    rows = db.get_public_notes_for_teacher(user["id"])
    return [dict(r) for r in rows]


@router.get("", summary="学生查看自己的笔记")
def get_my_notes(course_key: str | None = None, user=Depends(get_current_user)):
    rows = db.get_student_notes(user["id"], course_key)
    return [dict(r) for r in rows]


@router.post("", summary="新建笔记（学生）")
def create_note(request: NoteCreate, user=Depends(get_current_user)):
    is_public = request.is_public and bool(request.course_key)
    note_id = db.create_note(
        user["id"], request.course_key, request.doc_name,
        request.page_num, request.content, is_public,
        title=request.title, is_ai=request.is_ai,
    )
    return {"id": note_id}


@router.put("/{note_id}", summary="修改笔记（学生）")
def update_note(note_id: int, request: NoteUpdate, user=Depends(get_current_user)):
    is_public = request.is_public
    if is_public and request.course_key is not None and not request.course_key:
        is_public = False
    ok = db.update_note(note_id, user["id"], title=request.title, content=request.content,
                        is_public=is_public, course_key=request.course_key)
    if not ok:
        raise HTTPException(status_code=404, detail="笔记不存在或无权限")
    return {"ok": True}


@router.delete("/{note_id}", summary="删除笔记（学生）")
def delete_note(note_id: int, user=Depends(get_current_user)):
    ok = db.delete_note(note_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="笔记不存在或无权限")
    return {"ok": True}


@router.get("/{note_id}/comments", summary="获取笔记评论列表")
def get_comments(note_id: int, user=Depends(get_current_user)):
    rows = db.get_note_comments(note_id)
    return [dict(r) for r in rows]


@router.post("/{note_id}/comments", summary="教师评论笔记")
def add_comment(note_id: int, request: NoteCommentCreate, user=Depends(get_current_user)):
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可评论")
    comment_id = db.add_note_comment(note_id, user["id"], request.content)
    return {"id": comment_id}
