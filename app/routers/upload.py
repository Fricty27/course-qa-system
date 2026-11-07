import asyncio
import json
import os
import threading

import fitz
from fastapi import APIRouter, UploadFile, Form, Depends
from fastapi.responses import StreamingResponse

from app.routers.auth import require_teacher
from app.services.document_processor import process_pdf
from app.services.vector_store import add_chunks, get_collection

os.makedirs("data/uploads", exist_ok=True)

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", summary="上传课程文档（教师）")
async def upload_document(
    file: UploadFile,
    course_id: str = Form(...),
    teacher=Depends(require_teacher),
):
    content = await file.read()
    save_path = f"data/uploads/{course_id}_{file.filename}"
    filename = file.filename

    async def event_stream():
        with open(save_path, "wb") as f:
            f.write(content)

        try:
            doc = fitz.open(save_path)
            total = len(doc)
            doc.close()
        except Exception:
            total = 0

        yield f"data: {json.dumps({'type': 'start', 'total': total, 'filename': filename}, ensure_ascii=False)}\n\n"

        loop = asyncio.get_running_loop()
        q: asyncio.Queue = asyncio.Queue()

        def _run_processing():
            try:
                def on_progress(current, total_pages):
                    asyncio.run_coroutine_threadsafe(
                        q.put(("progress", current, total_pages)), loop
                    )

                chunks = process_pdf(save_path, course_id, progress_callback=on_progress)
                asyncio.run_coroutine_threadsafe(
                    q.put(("vectorizing", len(chunks))), loop
                )

                def on_embed_progress(done, total_chunks):
                    asyncio.run_coroutine_threadsafe(
                        q.put(("embed_progress", done, total_chunks)), loop
                    )

                collection = get_collection(course_id)
                add_chunks(collection, chunks, progress_callback=on_embed_progress)
                asyncio.run_coroutine_threadsafe(q.put(("done", len(chunks))), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(q.put(("error", str(e))), loop)

        threading.Thread(target=_run_processing, daemon=True).start()

        while True:
            item = await q.get()
            if item[0] == "progress":
                _, current, total_pages = item
                yield f"data: {json.dumps({'type': 'progress', 'current': current, 'total': total_pages}, ensure_ascii=False)}\n\n"
            elif item[0] == "vectorizing":
                total_chunks = item[1]
                yield f"data: {json.dumps({'type': 'vectorizing', 'total': total_chunks}, ensure_ascii=False)}\n\n"
            elif item[0] == "embed_progress":
                _, done, total_chunks = item
                yield f"data: {json.dumps({'type': 'embed_progress', 'done': done, 'total': total_chunks}, ensure_ascii=False)}\n\n"
            elif item[0] == "done":
                chunk_count = item[1]
                msg = f"✅ 《{filename}》处理完成！共 {chunk_count} 个文本块，已存入向量库。"
                yield f"data: {json.dumps({'type': 'done', 'chunks': chunk_count, 'message': msg}, ensure_ascii=False)}\n\n"
                break
            elif item[0] == "error":
                yield f"data: {json.dumps({'type': 'error', 'message': f'❌ 处理失败：{item[1]}'}, ensure_ascii=False)}\n\n"
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
