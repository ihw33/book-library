# 📚 Book Library

개인 소장 PDF 도서를 도서관처럼 탐색하고 검색하는 웹 앱.

## 기능

- **커버 그리드**: 실제 책 표지 이미지 (ISBN 매칭 via Google Books API)
- **전문 검색**: PDF 내용까지 검색 (SQLite FTS5)
- **카테고리 필터**: 13개 카테고리별 분류
- **반응형 + PWA**: 데스크톱 / iPad / iPhone / Galaxy Fold 지원
- **PDF 열기**: 클릭 시 기기 기본 PDF 뷰어로 열기

## 스택

| 레이어 | 기술 |
|--------|------|
| 백엔드 | FastAPI (Python) + SQLite FTS5 |
| 인덱서 | PyMuPDF + Google Books API |
| 프론트 | Next.js 14 + Tailwind CSS |
| 검색 | SQLite FTS5 (전문 검색) |

## 구조

```
book-library/
├── backend/
│   ├── main.py        # FastAPI 서버 (포트 8002)
│   ├── indexer.py     # PDF 스캔 → SQLite 인덱싱
│   ├── db.py          # SQLite 스키마
│   └── requirements.txt
├── frontend/          # Next.js 14 (포트 3001)
│   └── app/
└── data/
    ├── books.db       # SQLite DB
    └── covers/        # 표지 썸네일 캐시
```

## 시작하기

```bash
# 백엔드
cd backend
pip install -r requirements.txt
python main.py

# 첫 실행 — 인덱싱 (약 10~30분)
curl -X POST http://localhost:8002/books/reindex

# 프론트엔드
cd frontend
npm install
npm run dev
```

브라우저: `http://localhost:3001`

## PDF 소스

`/Users/m4_macbook/Dropbox/16.스캔도서/` (778개 PDF, 13개 카테고리, 37GB)
