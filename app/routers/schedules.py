from fastapi import APIRouter, Depends, HTTPException, Query
from app.models import ScheduleCreate, ScheduleUpdate, PublicScheduleCreate
from app.routers.auth import get_current_user
from app.services import database as db

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


# 注意：/dots、/public、/notifications 须在 /{id} 之前注册

@router.get("/dots", summary="获取当月日历点位（蓝/红/未读）")
def get_calendar_dots(
    year: int = Query(...),
    month: int = Query(...),
    user=Depends(get_current_user),
):
    return db.get_calendar_dots(user["id"], year, month)


@router.get("/public", summary="获取可见的公开日程")
def list_public_schedules(
    year: int = Query(...),
    month: int = Query(...),
    user=Depends(get_current_user),
):
    rows = db.get_public_schedules_for_user(user["id"], year, month)
    return [dict(r) for r in rows]


@router.post("/public", summary="教师创建公开日程")
def create_public_schedule(body: PublicScheduleCreate, user=Depends(get_current_user)):
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可创建公开日程")
    schedule_id = db.create_public_schedule(
        user["id"], body.course_key, body.date, body.title, body.content
    )
    return {"id": schedule_id}


@router.delete("/public/{schedule_id}", summary="教师取消公开日程")
def cancel_public_schedule(schedule_id: int, user=Depends(get_current_user)):
    if user["role"] != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可取消公开日程")
    ok = db.cancel_public_schedule(schedule_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="日程不存在或无权操作")
    return {"status": "ok"}


@router.post("/public/{schedule_id}/read", summary="学生标记公开日程已读")
def mark_public_read(schedule_id: int, user=Depends(get_current_user)):
    db.mark_public_schedule_read(user["id"], schedule_id)
    return {"status": "ok"}


@router.get("/notifications", summary="获取未展示的日程通知")
def get_notifications(user=Depends(get_current_user)):
    rows = db.get_unshown_notifications(user["id"])
    return [dict(r) for r in rows]


@router.post("/notifications/{notification_id}/shown", summary="标记通知已展示")
def mark_notification_shown(notification_id: int, user=Depends(get_current_user)):
    db.mark_notification_shown(notification_id, user["id"])
    return {"status": "ok"}


@router.get("", summary="获取当月个人日程")
def list_schedules(
    year: int = Query(...),
    month: int = Query(...),
    user=Depends(get_current_user),
):
    rows = db.get_user_schedules(user["id"], year, month)
    return [dict(r) for r in rows]


@router.post("", summary="创建个人日程")
def create_schedule(body: ScheduleCreate, user=Depends(get_current_user)):
    schedule_id = db.create_schedule(user["id"], body.date, body.title, body.content)
    return {"id": schedule_id}


@router.put("/{schedule_id}", summary="更新个人日程")
def update_schedule(schedule_id: int, body: ScheduleUpdate, user=Depends(get_current_user)):
    ok = db.update_schedule(schedule_id, user["id"], body.title, body.content)
    if not ok:
        raise HTTPException(status_code=404, detail="日程不存在或无权操作")
    return {"status": "ok"}


@router.delete("/{schedule_id}", summary="删除个人日程")
def delete_schedule(schedule_id: int, user=Depends(get_current_user)):
    ok = db.delete_schedule(schedule_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="日程不存在或无权操作")
    return {"status": "ok"}
