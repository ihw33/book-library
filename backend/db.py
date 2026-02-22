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

        CREATE TABLE IF NOT EXISTS tags (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS book_tags (
            book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
            tag_id  INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            PRIMARY KEY (book_id, tag_id)
        );

        CREATE INDEX IF NOT EXISTS idx_book_tags_book ON book_tags(book_id);
        CREATE INDEX IF NOT EXISTS idx_book_tags_tag  ON book_tags(tag_id);

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


def set_book_tags(book_id: int, tag_names: list[str]):
    """책의 태그 전체 교체 (기존 삭제 후 새로 삽입)."""
    if not tag_names:
        return
    conn = get_conn()
    cur = conn.cursor()
    # 기존 태그 연결 삭제
    cur.execute("DELETE FROM book_tags WHERE book_id = ?", (book_id,))
    for name in tag_names:
        name = name.strip()
        if not name:
            continue
        # 태그 upsert
        cur.execute("INSERT OR IGNORE INTO tags(name) VALUES(?)", (name,))
        tag_id = cur.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()[0]
        cur.execute("INSERT OR IGNORE INTO book_tags(book_id, tag_id) VALUES(?,?)", (book_id, tag_id))
    conn.commit()
    conn.close()


def add_book_tag(book_id: int, tag_name: str):
    """책에 태그 1개 추가."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO tags(name) VALUES(?)", (tag_name,))
    tag_id = cur.execute("SELECT id FROM tags WHERE name = ?", (tag_name,)).fetchone()[0]
    cur.execute("INSERT OR IGNORE INTO book_tags(book_id, tag_id) VALUES(?,?)", (book_id, tag_id))
    conn.commit()
    conn.close()


def remove_book_tag(book_id: int, tag_name: str):
    """책에서 태그 1개 제거."""
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT id FROM tags WHERE name = ?", (tag_name,)).fetchone()
    if row:
        cur.execute("DELETE FROM book_tags WHERE book_id = ? AND tag_id = ?", (book_id, row[0]))
    conn.commit()
    conn.close()


def get_book_tags(book_id: int) -> list[str]:
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT t.name FROM tags t
        JOIN book_tags bt ON t.id = bt.tag_id
        WHERE bt.book_id = ?
        ORDER BY t.name
    """, (book_id,)).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_all_tags():
    """태그 목록 + 책 수."""
    conn = get_conn()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT t.name, COUNT(bt.book_id) as count
        FROM tags t
        JOIN book_tags bt ON t.id = bt.tag_id
        GROUP BY t.name
        ORDER BY count DESC, t.name
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_fts_content(book_id: int, content: str):
    """FTS 전문 내용 업데이트."""
    conn = get_conn()
    cur = conn.cursor()
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


def search_books(query: str, category: str = "", tag: str = "", page: int = 1, size: int = 40):
    conn = get_conn()
    cur = conn.cursor()
    offset = (page - 1) * size

    # 태그 필터용 서브쿼리
    tag_join = ""
    tag_filter = ""
    tag_params = []
    if tag:
        tag_join = "JOIN book_tags bt ON b.id = bt.book_id JOIN tags t ON bt.tag_id = t.id"
        tag_filter = "AND t.name = ?"
        tag_params = [tag]

    if query:
        sql = f"""
            SELECT b.*, bm25(books_fts) as score
            FROM books_fts
            JOIN books b ON books_fts.rowid = b.id
            {tag_join}
            WHERE books_fts MATCH ?
            {"AND b.category LIKE ?" if category else ""}
            {tag_filter}
            ORDER BY score
            LIMIT ? OFFSET ?
        """
        params = [query]
        if category:
            params.append(f"%{category}%")
        params += tag_params + [size, offset]
    else:
        sql = f"""
            SELECT b.*, 0 as score FROM books b
            {tag_join}
            WHERE 1=1
            {"AND b.category LIKE ?" if category else ""}
            {tag_filter}
            ORDER BY b.category, b.title
            LIMIT ? OFFSET ?
        """
        params = []
        if category:
            params.append(f"%{category}%")
        params += tag_params + [size, offset]

    rows = cur.execute(sql, params).fetchall()

    # 전체 수 카운트
    count_sql = f"""
        SELECT COUNT(DISTINCT b.id) FROM books b
        {tag_join}
        WHERE 1=1
        {"AND b.category LIKE ?" if category else ""}
        {tag_filter}
    """
    count_params = []
    if category:
        count_params.append(f"%{category}%")
    count_params += tag_params
    total = cur.execute(count_sql, count_params).fetchone()[0]

    conn.close()

    # 각 책에 태그 목록 첨부
    result = []
    for r in rows:
        book = dict(r)
        book["tags"] = get_book_tags(book["id"])
        result.append(book)

    return result, total


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
    if not row:
        return None
    book = dict(row)
    book["tags"] = get_book_tags(book_id)
    return book
