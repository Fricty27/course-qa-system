from fastapi import APIRouter, Depends, HTTPException, Query
from app.models import GroupMessageCreate, PinRequest
from app.routers.auth import get_current_user
from app.services import database as db

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("", summary="获取当前用户的群组列表（含未读数）")
def list_groups(user=Depends(get_current_user)):
    rows = db.get_user_groups_with_unread(user["id"])
    return [dict(r) for r in rows]


@router.get("/unread-total", summary="获取所有群组的未读消息总数")
def group_unread_total(user=Depends(get_current_user)):
    return {"count": db.get_group_unread_total(user["id"])}


# 注意：/{group_id}/members, /pins, /dates 须在 /{group_id}/messages 之前注册

@router.get("/{group_id}/members", summary="获取群组成员列表")
def get_group_members(group_id: int, user=Depends(get_current_user)):
    rows = db.get_group_members(group_id)
    return [dict(r) for r in rows]


@router.get("/{group_id}/pins", summary="获取群组置顶消息")
def get_group_pins(group_id: int, user=Depends(get_current_user)):
    rows = db.get_group_pins(group_id)
    return [dict(r) for r in rows]


@router.put("/{group_id}/pins", summary="置顶群消息（仅教师，最多2条）")
def pin_group_message(group_id: int, body: PinRequest, user=Depends(get_current_user)):
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可置顶群消息")
    db.pin_group_message(group_id, body.message_id, user["id"])
    return {"status": "ok"}


@router.delete("/{group_id}/pins/{message_id}", summary="取消群消息置顶（仅教师）")
def unpin_group_message(group_id: int, message_id: int, user=Depends(get_current_user)):
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可取消置顶")
    db.unpin_group_message(group_id, message_id)
    return {"status": "ok"}


@router.get("/{group_id}/dates", summary="获取群组有消息的日期列表")
def group_dates(group_id: int, user=Depends(get_current_user)):
    return db.get_group_dates(group_id)


@router.get("/{group_id}/messages", summary="获取群组消息（可按日期筛选）")
def get_group_messages(
    group_id: int,
    date: str | None = Query(default=None),
    user=Depends(get_current_user),
):
    rows = db.get_group_messages(group_id, date)
    db.mark_group_read(group_id, user["id"])
    return [dict(r) for r in rows]


@router.post("/{group_id}/messages", summary="发送群组消息")
def send_group_message(group_id: int, body: GroupMessageCreate, user=Depends(get_current_user)):
    msg_id = db.send_group_message(group_id, user["id"], body.content)
    return {"id": msg_id}
