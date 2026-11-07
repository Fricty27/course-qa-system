import asyncio
import json
import threading
from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from app.models import QueryRequest
from app.routers.auth import get_current_user
from app.services.rag import rag_answer, ranked_search
from app.services.llm import generate_answer_stream
from app.services import database as db

router = APIRouter(prefix="/api", tags=["query"])


def _log_query(user, request: QueryRequest, answer: str) -> None:
    course = db.get_course_by_key(request.course_id)
    db.log_question(
        student_id=user["id"] if user else None,
        student_name=user["username"] if user else "匿名",
        course_key=request.course_id,
        course_name=course["name"] if course else request.course_id,
        question=request.question,
        answer=answer,
    )


def _optional_user(authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        return None
    try:
        return get_current_user(authorization)
    except Exception:
        return None


@router.post("/query", summary="提出问题")
async def ask_question(
    request: QueryRequest,
    user=Depends(_optional_user),
):
    try:
        result = await asyncio.to_thread(rag_answer, request.question, request.course_id)

        _log_query(user, request, result["answer"])

        return {
            "question": request.question,
            "answer": result["answer"],
            "sources": result["sources"],
            "chunks": [
                {
                    "text": c["text"][:400] + "..." if len(c["text"]) > 400 else c["text"],
                    "source": f"《{c['doc_name']}》 第 {c['page_num']} 页",
                }
                for c in result["chunks"]
            ],
        }
    except Exception as e:
        return {
            "question": request.question,
            "answer": "",
            "sources": [],
            "chunks": [],
            "error": str(e),
        }


@router.post("/query/stream", summary="流式提问（SSE）")
async def ask_question_stream(
    request: QueryRequest,
    user=Depends(_optional_user),
):
    async def event_stream():
        # 第一步：语义检索
        try:
            chunks = await asyncio.to_thread(
                ranked_search, request.question, request.course_id
            )
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            return

        if not chunks:
            yield f"data: {json.dumps({'type': 'chunks', 'chunks': [], 'sources': []})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'answer': ''})}\n\n"
            return

        sources = [{"doc_name": c["doc_name"], "page_num": c["page_num"]} for c in chunks]
        chunks_data = [
            {
                "text": c["text"][:400] + "..." if len(c["text"]) > 400 else c["text"],
                "source": f"《{c['doc_name']}》 第 {c['page_num']} 页",
                "doc_name": c["doc_name"],
                "page_num": c["page_num"],
            }
            for c in chunks
        ]
        yield f"data: {json.dumps({'type': 'chunks', 'chunks': chunks_data, 'sources': sources}, ensure_ascii=False)}\n\n"

        # 第二步：流式 LLM 回答（同步生成器运行在后台线程）
        full_answer = ""
        try:
            loop = asyncio.get_running_loop()
            q: asyncio.Queue = asyncio.Queue()

            def _run_stream():
                try:
                    for token in generate_answer_stream(request.question, chunks):
                        asyncio.run_coroutine_threadsafe(q.put(token), loop)
                except Exception:
                    pass
                finally:
                    asyncio.run_coroutine_threadsafe(q.put(None), loop)

            threading.Thread(target=_run_stream, daemon=True).start()

            while True:
                token = await q.get()
                if token is None:
                    break
                full_answer += token
                yield f"data: {json.dumps({'type': 'token', 'content': token}, ensure_ascii=False)}\n\n"
        except Exception:
            pass

        try:
            _log_query(user, request, full_answer)
        except Exception:
            pass

        yield f"data: {json.dumps({'type': 'done', 'answer': full_answer}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
