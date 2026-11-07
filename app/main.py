import os
from dotenv import load_dotenv
load_dotenv()
os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers.upload import router as upload_router
from app.routers.query import router as query_router
from app.routers.auth import router as auth_router
from app.routers.courses import router as courses_router
from app.routers.history import router as history_router
from app.routers.documents import router as documents_router
from app.routers.messages import router as messages_router
from app.routers.notes import router as notes_router
from app.routers.groups import router as groups_router
from app.routers.schedules import router as schedules_router
from app.services.database import init_db

init_db()

app = FastAPI(
    title="CourseQA - 课程智能问答辅助系统",
    description="基于课程教材的智能语义问答系统，支持文档上传与精准页码定位",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/pdfs", StaticFiles(directory="data/uploads"), name="pdfs")
app.include_router(auth_router)
app.include_router(courses_router)
app.include_router(history_router)
app.include_router(upload_router)
app.include_router(query_router)
app.include_router(documents_router)
app.include_router(messages_router)
app.include_router(notes_router)
app.include_router(groups_router)
app.include_router(schedules_router)


@app.get("/")
async def root():
    return {"message": "✅ CourseQA 系统已成功启动！请访问 /docs"}


if __name__ == "__main__":
    import uvicorn
    print("🤔 正在启动 CourseQA 系统...")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=False)
