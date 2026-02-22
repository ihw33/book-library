# Book Library — CLAUDE.md

## 프로젝트 개요
개인 소장 PDF 788개를 도서관처럼 탐색/검색하는 로컬 웹 앱.

## 핵심 규칙
- 시킨 것만 하기
- 초안 먼저 보여주기

## PDF 소스 경로
`/Users/m4_macbook/Dropbox/16.스캔도서/`
- 788개 PDF, 13개 카테고리, 37GB
- OCR 이미 적용됨 → PyMuPDF 텍스트 추출 가능

## 아키텍처
- **백엔드**: FastAPI (포트 8002), venv: `backend/venv/`
- **프론트**: Next.js 14 (포트 3001)
- **DB**: SQLite FTS5 (`data/books.db`)
- **표지**: 알라딘 API (1순위) + Google Books API (2순위)
- **태그**: 알라딘 카테고리 + 키워드 규칙 병합 (40개 태그, 98% 커버)

## 카테고리 구조 (알라딘 기반 재구성 완료)
01-IT-프로그래밍(172), 02-외국어(191), 03-경제-경영(83),
04-자기계발(46), 05-인문학(84), 06-역사(21),
07-과학-수학(40), 08-예술-문화(51), 09-문학(29),
10-사회-시사(16), 11-건강-취미(17), 12-종교-신비학(18), 99-기타(20)
- 각 카테고리에 알라딘 중분류 기반 하위폴더 있음

## 핵심 파일
- `backend/main.py` — FastAPI 서버 (포트 8002)
- `backend/indexer.py` — PDF 스캔 + 알라딘/Google Books + 자동태깅
- `backend/db.py` — SQLite FTS5 + 태그 시스템
- `backend/tagger.py` — 키워드 기반 자동 태깅 (38 규칙 + 폴더 fallback)
- `backend/aladin.py` — 알라딘 API 연동 (ttbkey: .env)
- `backend/migrate_folders.py` — 폴더 재구성 스크립트
- `frontend/app/page.tsx` — 메인 (폴더/태그 사이드바 + 검색 + 커버 그리드)

## 현재 상태 (2026-02-22)
- 마지막 커밋: `5b4cfb2` (카테고리 색상 매핑 업데이트)
- 완료: 백엔드+프론트 구현, 태그 시스템, 알라딘 API, 폴더 재구성
- PR: #6~#9 머지 완료
- 남은 이슈: PWA 서비스워커/아이콘 (이슈 #5)

## 개발 주의사항
- 백엔드 포트: 8002 (StockIQ 8001과 충돌 방지)
- 프론트 포트: 3001 (StockIQ 3000과 충돌 방지)
- Dropbox 경로 하드코딩 금지 → .env로 관리
- macOS HFS+ NFD 인코딩: unicodedata.normalize("NFC") 필수
- 알라딘 API 키: .env의 ALADIN_KEY
