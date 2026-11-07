from fastapi import APIRouter, Depends, HTTPException, Query
from app.models import MessageCreate, PinRequest
from app.routers.auth import get_current_user
from app.services import database as db

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("/unread-count", summary="获取未读消息数")
def get_unread_count(user=Depends(get_current_user)):
    return {"count": db.get_unread_count(user["id"])}


@router.get("/conversations", summary="获取会话列表")
def get_conversations(user=Depends(get_current_user)):
    rows = db.get_conversations(user["id"])
    return [dict(r) for r in rows]


# 注意：以下路由须在 /conversation/{other_user_id} 之前注册，避免被通配符覆盖

@router.get("/conversation/{other_user_id}/pin", summary="获取置顶消息")
def get_pin(other_user_id: int, user=Depends(get_current_user)):
    row = db.get_private_pin(user["id"], other_user_id)
    return dict(row) if row else None


@router.put("/conversation/{other_user_id}/pin", summary="置顶消息")
def set_pin(other_user_id: int, body: PinRequest, user=Depends(get_current_user)):
    db.set_private_pin(user["id"], other_user_id, body.message_id)
    return {"status": "ok"}


@router.delete("/conversation/{other_user_id}/pin", summary="取消置顶")
def delete_pin(other_user_id: int, user=Depends(get_current_user)):
    db.delete_private_pin(user["id"], other_user_id)
    return {"status": "ok"}


@router.get("/conversation/{other_user_id}/dates", summary="获取有消息的日期列表")
def get_dates(other_user_id: int, user=Depends(get_current_user)):
    return db.get_conversation_dates(user["id"], other_user_id)


@router.get("/conversation/{other_user_id}/history", summary="获取某日期的历史消息")
def get_history(other_user_id: int, date: str = Query(...), user=Depends(get_current_user)):
    rows = db.get_conversation_messages_by_date(user["id"], other_user_id, date)
    return [dict(r) for r in rows]


@router.get("/conversation/{other_user_id}", summary="获取与某用户的消息（同时标为已读）")
def get_conversation(other_user_id: int, user=Depends(get_current_user)):
    rows = db.get_conversation_messages(user["id"], other_user_id)
    return [dict(r) for r in rows]


@router.post("", summary="发送消息")
def send_message(request: MessageCreate, user=Depends(get_current_user)):
    msg_id = db.send_message(user["id"], request.receiver_id, request.content, request.course_key)
    return {"id": msg_id}
