"""
PDF 인덱서
- Dropbox 폴더 재귀 스캔
- 파일명 파싱 → 제목/저자 추출
- PyMuPDF로 ISBN 탐지 + 텍스트 추출
- Google Books API로 메타데이터 + 표지 수집
- SQLite에 저장
"""

import re
import os
import asyncio
import httpx
import fitz  # PyMuPDF
from pathlib import Path
from dotenv import load_dotenv
from db import init_db, upsert_book, update_fts_content, set_book_tags
from tagger import auto_tag
from aladin import search_aladin

load_dotenv(Path(__file__).parent.parent / ".env")

PDF_ROOT = Path(os.getenv("PDF_ROOT", "/Users/m4_macbook/Dropbox/16.스캔도서"))
COVERS_DIR = Path(__file__).parent.parent / "data" / "covers"
COVERS_DIR.mkdir(parents=True, exist_ok=True)

# 제외 폴더 (Python 환경 등)
SKIP_DIRS = {"pdf_search_env", "pdf_search_tools", ".dropbox"}

ISBN_PATTERN = re.compile(
    r'(?:ISBN[-—\s]?(?:13|10)?:?\s*)?'
    r'(97[89][-\s]?(?:\d[-\s]?){9}\d|(?:\d[-\s]?){9}[\dXx])',
    re.IGNORECASE
)
AUTHOR_TITLE_PATTERN = re.compile(r'^\[(.+?)\]\s*(.+)$')


# ─── 파일명 파싱 ─────────────────────────────────────────────

def parse_filename(stem: str) -> tuple[str, str]:
    """'[저자] 제목' 패턴에서 (title, author) 반환."""
    m = AUTHOR_TITLE_PATTERN.match(stem)
    if m:
        return m.group(2).strip(), m.group(1).strip()
    return stem.strip(), ""


def parse_category(filepath: Path) -> str:
    """상위 폴더명에서 카테고리 추출."""
    parts = filepath.relative_to(PDF_ROOT).parts
    if len(parts) >= 2:
        return parts[0]  # 최상위 카테고리 폴더
    return "99-기타-미분류"


# ─── ISBN 추출 ───────────────────────────────────────────────

def extract_isbn(pdf_path: Path, max_pages: int = 5) -> str:
    try:
        doc = fitz.open(str(pdf_path))
        for i in range(min(max_pages, len(doc))):
            text = doc[i].get_text()
            m = ISBN_PATTERN.search(text)
            if m:
                isbn = re.sub(r'[-\s]', '', m.group(1))
                return isbn
        doc.close()
    except Exception:
        pass
    return ""


def extract_text(pdf_path: Path, max_pages: int = 10) -> str:
    """FTS용 텍스트 추출 (처음 N 페이지)."""
    try:
        doc = fitz.open(str(pdf_path))
        texts = []
        for i in range(min(max_pages, len(doc))):
            texts.append(doc[i].get_text())
        doc.close()
        return "\n".join(texts)[:50000]  # 50KB 제한
    except Exception:
        return ""


def get_page_count(pdf_path: Path) -> int:
    try:
        doc = fitz.open(str(pdf_path))
        count = len(doc)
        doc.close()
        return count
    except Exception:
        return 0


def extract_cover(pdf_path: Path, book_id_placeholder: str) -> str:
    """첫 페이지를 PNG로 저장. 경로 반환."""
    cover_path = COVERS_DIR / f"{book_id_placeholder}.png"
    if cover_path.exists():
        return str(cover_path)
    try:
        doc = fitz.open(str(pdf_path))
        page = doc[0]
        mat = fitz.Matrix(1.5, 1.5)  # 150% 해상도
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(cover_path))
        doc.close()
        return str(cover_path)
    except Exception:
        return ""


# ─── Google Books API ────────────────────────────────────────

async def fetch_google_books(client: httpx.AsyncClient, query: str, by_isbn: bool = False) -> dict:
    """Google Books API로 메타데이터 수집."""
    try:
        if by_isbn:
            url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{query}&maxResults=1"
        else:
            url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=1"

        r = await client.get(url, timeout=10)
        data = r.json()
        if data.get("totalItems", 0) == 0:
            return {}
        item = data["items"][0]["volumeInfo"]
        return {
            "title_api": item.get("title", ""),
            "author": ", ".join(item.get("authors", [])),
            "publisher": item.get("publisher", ""),
            "description": item.get("description", "")[:500],
            "cover_url": (item.get("imageLinks", {}).get("thumbnail", "")
                         .replace("http://", "https://")
                         .replace("&zoom=1", "&zoom=2")),
        }
    except Exception:
        return {}


# ─── 메인 인덱서 ─────────────────────────────────────────────

async def index_all(progress_callback=None):
    """전체 PDF 스캔 및 인덱싱."""
    init_db()

    pdf_files = []
    for root, dirs, files in os.walk(PDF_ROOT):
        # 제외 폴더 스킵
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        for f in files:
            if f.lower().endswith(('.pdf', '.epub')):
                pdf_files.append(Path(root) / f)

    total = len(pdf_files)
    print(f"[인덱서] PDF {total}개 발견")

    async with httpx.AsyncClient() as client:
        for i, pdf_path in enumerate(pdf_files, 1):
            try:
                await _index_one(client, pdf_path, i, total, progress_callback)
            except Exception as e:
                print(f"  [오류] {pdf_path.name}: {e}")

    print(f"[인덱서] 완료! {total}개 처리")


async def _index_one(client, pdf_path: Path, idx: int, total: int, progress_callback=None):
    stem = pdf_path.stem
    title, author = parse_filename(stem)
    category = parse_category(pdf_path)
    filesize = pdf_path.stat().st_size

    print(f"[{idx}/{total}] {stem[:50]}")

    # ISBN 추출
    isbn = extract_isbn(pdf_path)

    # 1순위: 알라딘 API (한국 책 분류 정확)
    aladin = {}
    if isbn:
        aladin = await search_aladin(client, isbn=isbn)
    if not aladin and title:
        import unicodedata
        q = unicodedata.normalize("NFC", title)
        aladin = await search_aladin(client, title=q)

    # 2순위: Google Books (영어 책 fallback)
    google = {}
    if not aladin:
        if isbn:
            google = await fetch_google_books(client, isbn, by_isbn=True)
        if not google and title:
            query = f"{title} {author}".strip()
            google = await fetch_google_books(client, query, by_isbn=False)

    # 메타데이터 병합 — 알라딘 > Google > 파일명
    meta = aladin or google
    final_author = author or meta.get("author", "")
    final_title = title  # 파일명 제목 유지
    cover_url = meta.get("cover_url", "")
    isbn = isbn or meta.get("isbn", "")

    # 페이지 수
    page_count = get_page_count(pdf_path)

    # DB 저장
    data = {
        "title": final_title,
        "author": final_author,
        "category": category,
        "publisher": meta.get("publisher", ""),
        "description": meta.get("description", ""),
        "isbn": isbn,
        "cover_url": cover_url,
        "cover_local": "",  # 나중에 업데이트
        "filepath": str(pdf_path),
        "filesize": filesize,
        "page_count": page_count,
    }
    book_id = upsert_book(data)

    # 로컬 표지 생성
    cover_local = extract_cover(pdf_path, str(book_id))
    if cover_local:
        from db import get_conn
        conn = get_conn()
        conn.execute("UPDATE books SET cover_local = ? WHERE id = ?", (cover_local, book_id))
        conn.commit()
        conn.close()

    # 자동 태깅: 키워드 규칙 + 알라딘 카테고리 병합
    keyword_tags = auto_tag(final_title, str(pdf_path))
    api_tags = aladin.get("category_tags", [])
    merged_tags = sorted(set(keyword_tags) | set(api_tags))
    set_book_tags(book_id, merged_tags)

    # FTS 텍스트 인덱싱
    text = extract_text(pdf_path)
    if text.strip():
        update_fts_content(book_id, text)

    if progress_callback:
        progress_callback(idx, total, final_title)

    # API 요청 간격 (과도한 요청 방지)
    await asyncio.sleep(0.2)


if __name__ == "__main__":
    asyncio.run(index_all())
