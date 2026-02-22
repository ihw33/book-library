import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "books.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS books (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            author      TEXT DEFAULT '',
            category    TEXT DEFAULT '',
            publisher   TEXT DEFAULT '',
            description TEXT DEFAULT '',
            isbn        TEXT DEFAULT '',
            cover_url   TEXT DEFAULT '',
            cover_local TEXT DEFAULT '',
            filepath    TEXT NOT NULL UNIQUE,
            filesize    INTEGER DEFAULT 0,
            page_count  INTEGER DEFAULT 0,
            indexed_at  TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS books_fts USING fts5(
            title,
            author,
            category,
            description,
            content,
            content='books',
            content_rowid='id',
            tokenize='unicode61'
        );

        CREATE TRIGGER IF NOT EXISTS books_ai AFTER INSERT ON books BEGIN
            INSERT INTO books_fts(rowid, title, author, category, description, content)
            VALUES (new.id, new.title, new.author, new.category, new.description, '');
        END;

        CREATE TRIGGER IF NOT EXISTS books_au AFTER UPDATE ON books BEGIN
            INSERT INTO books_fts(books_fts, rowid, title, author, category, description, content)
            VALUES ('delete', old.id, old.title, old.author, old.category, old.description, '');
            INSERT INTO books_fts(rowid, title, author, category, description, content)
            VALUES (new.id, new.title, new.author, new.category, new.description, '');
        END;

        CREATE TRIGGER IF NOT EXISTS books_ad AFTER DELETE ON books BEGIN
            INSERT INTO books_fts(books_fts, rowid, title, author, category, description, content)
            VALUES ('delete', old.id, old.title, old.author, old.category, old.description, '');
        END;
    """)

    conn.commit()
    conn.close()
    print(f"[DB] 초기화 완료: {DB_PATH}")


def upsert_book(data: dict) -> int:
    """책 정보 삽입 또는 업데이트. book id 반환."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO books (title, author, category, publisher, description,
                           isbn, cover_url, cover_local, filepath, filesize, page_count)
        VALUES (:title, :author, :category, :publisher, :description,
                :isbn, :cover_url, :cover_local, :filepath, :filesize, :page_count)
        ON CONFLICT(filepath) DO UPDATE SET
            title       = excluded.title,
            author      = excluded.author,
            category    = excluded.category,
            publisher   = excluded.publisher,
            description = excluded.description,
            isbn        = excluded.isbn,
            cover_url   = excluded.cover_url,
            cover_local = excluded.cover_local,
            filesize    = excluded.filesize,
            page_count  = excluded.page_count,
            indexed_at  = datetime('now', 'localtime')
    """, data)
    book_id = cur.lastrowid or cur.execute(
        "SELECT id FROM books WHERE filepath = ?", (data["filepath"],)
    ).fetchone()[0]
    conn.commit()
    conn.close()
    return book_id


def update_fts_content(book_id: int, content: str):
    """FTS 전문 내용 업데이트 (본문 텍스트)."""
    conn = get_conn()
    cur = conn.cursor()
    # 기존 FTS 항목 삭제 후 재삽입
    cur.execute("INSERT INTO books_fts(books_fts, rowid) VALUES('delete', ?)", (book_id,))
    row = cur.execute(
        "SELECT title, author, category, description FROM books WHERE id = ?", (book_id,)
    ).fetchone()
    if row:
        cur.execute(
            "INSERT INTO books_fts(rowid, title, author, category, description, content) VALUES (?,?,?,?,?,?)",
            (book_id, row["title"], row["author"], row["category"], row["description"], content)
        )
    conn.commit()
    conn.close()


def search_books(query: str, category: str = "", page: int = 1, size: int = 40):
    conn = get_conn()
    cur = conn.cursor()
    offset = (page - 1) * size

    if query:
        sql = """
            SELECT b.*, bm25(books_fts) as score
            FROM books_fts
            JOIN books b ON books_fts.rowid = b.id
            WHERE books_fts MATCH ?
            {cat_filter}
            ORDER BY score
            LIMIT ? OFFSET ?
        """
        cat_filter = "AND b.category LIKE ?" if category else ""
        sql = sql.format(cat_filter=cat_filter)
        params = [query, f"%{category}%", size, offset] if category else [query, size, offset]
    else:
        sql = """
            SELECT *, 0 as score FROM books
            WHERE 1=1
            {cat_filter}
            ORDER BY category, title
            LIMIT ? OFFSET ?
        """
        cat_filter = "AND category LIKE ?" if category else ""
        sql = sql.format(cat_filter=cat_filter)
        params = [f"%{category}%", size, offset] if category else [size, offset]

    rows = cur.execute(sql, params).fetchall()
    total = cur.execute(
        "SELECT COUNT(*) FROM books" + (" WHERE category LIKE ?" if category else ""),
        ([f"%{category}%"] if category else [])
    ).fetchone()[0]
    conn.close()
    return [dict(r) for r in rows], total


def get_categories():
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT category, COUNT(*) as count FROM books GROUP BY category ORDER BY category"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_book(book_id: int):
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
