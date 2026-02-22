"""
Book Library FastAPI 서버 (포트 8002)
"""

import asyncio
import json
import subprocess
import platform
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from db import (init_db, search_books, get_categories, get_book,
                get_all_tags, add_book_tag, remove_book_tag, set_book_tags)
from pydantic import BaseModel
import indexer as idx_module

app = FastAPI(title="Book Library API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 로컬 전용 — 모바일 포함 허용
    allow_methods=["*"],
    allow_headers=["*"],
)

COVERS_DIR = Path(__file__).parent.parent / "data" / "covers"

# ─── 인덱싱 상태 ────────────────────────────────────────────

_index_state = {
    "running": False,
    "current": 0,
    "total": 0,
    "current_title": "",
    "done": False,
    "error": "",
}


def _progress(idx: int, total: int, title: str):
    _index_state.update(current=idx, total=total, current_title=title)


async def _run_indexer():
    _index_state.update(running=True, done=False, error="", current=0)
    try:
        await idx_module.index_all(progress_callback=_progress)
        _index_state.update(done=True)
    except Exception as e:
        _index_state["error"] = str(e)
    finally:
        _index_state["running"] = False


# ─── 시작 ───────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    init_db()


# ─── 도서 목록 / 검색 ────────────────────────────────────────

@app.get("/books")
async def list_books(
    q: str = Query("", description="검색어"),
    category: str = Query("", description="카테고리 필터"),
    tag: str = Query("", description="태그 필터"),
    page: int = Query(1, ge=1),
    size: int = Query(40, ge=1, le=100),
):
    books, total = search_books(q, category, tag, page, size)
    return {
        "items": books,
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    }


@app.get("/books/{book_id}")
async def get_book_detail(book_id: int):
    book = get_book(book_id)
    if not book:
        raise HTTPException(404, "책을 찾을 수 없습니다")
    return book


# ─── 표지 이미지 ─────────────────────────────────────────────

@app.get("/books/{book_id}/cover")
async def get_cover(book_id: int):
    book = get_book(book_id)
    if not book:
        raise HTTPException(404, "책을 찾을 수 없습니다")

    # 로컬 표지 우선
    local = book.get("cover_local", "")
    if local and Path(local).exists():
        return FileResponse(local, media_type="image/png")

    # Google Books URL로 리다이렉트
    cover_url = book.get("cover_url", "")
    if cover_url:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(cover_url)

    raise HTTPException(404, "표지 없음")


# ─── PDF 스트리밍 (모바일) ───────────────────────────────────

@app.get("/books/{book_id}/stream")
async def stream_pdf(book_id: int):
    book = get_book(book_id)
    if not book:
        raise HTTPException(404, "책을 찾을 수 없습니다")

    filepath = Path(book["filepath"])
    if not filepath.exists():
        raise HTTPException(404, f"파일 없음: {filepath}")

    def iterfile():
        with open(filepath, "rb") as f:
            while chunk := f.read(64 * 1024):
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filepath.name}"',
            "Content-Length": str(filepath.stat().st_size),
        },
    )


# ─── PDF 열기 (macOS) ────────────────────────────────────────

@app.post("/books/{book_id}/open")
async def open_book(book_id: int):
    book = get_book(book_id)
    if not book:
        raise HTTPException(404, "책을 찾을 수 없습니다")

    filepath = book["filepath"]
    if not Path(filepath).exists():
        raise HTTPException(404, f"파일 없음: {filepath}")

    if platform.system() == "Darwin":
        subprocess.Popen(["open", filepath])
    elif platform.system() == "Linux":
        subprocess.Popen(["xdg-open", filepath])
    else:
        raise HTTPException(400, "이 OS에서는 자동 열기를 지원하지 않습니다")

    return {"ok": True, "filepath": filepath}


# ─── 카테고리 ────────────────────────────────────────────────

@app.get("/categories")
async def list_categories():
    return get_categories()


# ─── 태그 ────────────────────────────────────────────────────

@app.get("/tags")
async def list_tags():
    return get_all_tags()


class TagBody(BaseModel):
    tag: str


@app.post("/books/{book_id}/tags")
async def add_tag(book_id: int, body: TagBody):
    book = get_book(book_id)
    if not book:
        raise HTTPException(404, "책을 찾을 수 없습니다")
    add_book_tag(book_id, body.tag.strip())
    return {"ok": True, "tags": get_book(book_id)["tags"]}


@app.delete("/books/{book_id}/tags/{tag_name}")
async def delete_tag(book_id: int, tag_name: str):
    book = get_book(book_id)
    if not book:
        raise HTTPException(404, "책을 찾을 수 없습니다")
    remove_book_tag(book_id, tag_name)
    return {"ok": True, "tags": get_book(book_id)["tags"]}


# ─── 인덱싱 관리 ─────────────────────────────────────────────

@app.post("/admin/reindex")
async def reindex(background_tasks: BackgroundTasks):
    if _index_state["running"]:
        return JSONResponse({"ok": False, "message": "이미 인덱싱 중입니다"})
    background_tasks.add_task(_run_indexer)
    return {"ok": True, "message": "인덱싱 시작"}


@app.get("/admin/status")
async def index_status():
    return _index_state


@app.get("/admin/status/stream")
async def index_status_stream():
    """SSE로 인덱싱 진행률 실시간 전송."""
    async def event_gen():
        while _index_state["running"]:
            data = json.dumps(_index_state, ensure_ascii=False)
            yield f"data: {data}\n\n"
            await asyncio.sleep(1)
        # 완료 전송
        data = json.dumps(_index_state, ensure_ascii=False)
        yield f"data: {data}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# ─── 실행 ───────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
