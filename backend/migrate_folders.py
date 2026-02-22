"""
폴더 재구성 스크립트
- 알라딘 카테고리 기반으로 PDF 파일을 새 폴더로 이동
- 대분류 → 메인 폴더, 중분류 → 하위 폴더
- 이동 전 매핑 CSV 백업 생성
- DB filepath/category 업데이트
"""

import os
import csv
import shutil
import unicodedata
from pathlib import Path
from datetime import datetime
from db import get_conn

PDF_ROOT = Path(os.getenv("PDF_ROOT", "/Users/m4_macbook/Dropbox/16.스캔도서"))
BACKUP_CSV = Path(__file__).parent.parent / "data" / f"migration_backup_{datetime.now():%Y%m%d_%H%M%S}.csv"

# ─── 알라딘 대분류 → 메인 폴더 ──────────────────────────────

MAIN_FOLDER = {
    "컴퓨터/모바일": "01-IT-프로그래밍",
    "컴퓨터": "01-IT-프로그래밍",
    "외국어": "02-외국어",
    "경제경영": "03-경제-경영",
    "자기계발": "04-자기계발",
    "인문학": "05-인문학",
    "고전": "05-인문학",
    "역사": "06-역사",
    "과학": "07-과학-수학",
    "대학교재/전문서적": "07-과학-수학",
    "기술공학": "07-과학-수학",
    "예술/대중문화": "08-예술-문화",
    "건축/디자인": "08-예술-문화",
    "만화/라이트노벨": "08-예술-문화",
    "소설/시/희곡": "09-문학",
    "에세이": "09-문학",
    "사회과학": "10-사회-시사",
    "건강/취미": "11-건강-취미",
    "종교/역학": "12-종교-신비학",
    # 소규모 카테고리
    "청소년": "05-인문학",
    "어린이": "05-인문학",
    "좋은부모": "05-인문학",
    "유아": "05-인문학",
    "수험서/자격증": "07-과학-수학",
    "잡지": "99-기타",
    "여행": "11-건강-취미",
    "고등학교참고서": "07-과학-수학",
    "중학교참고서": "07-과학-수학",
    "초등학교참고서": "07-과학-수학",
    "교육/자료": "05-인문학",
}

# ─── 알라딘 중분류 → 하위 폴더명 매핑 ──────────────────────

SUB_FOLDER = {
    # 01-IT-프로그래밍
    "인공지능": "AI-인공지능",
    "프로그래밍 언어": "프로그래밍-언어",
    "프로그래밍 개발/방법론": "개발방법론",
    "컴퓨터 공학": "컴퓨터공학",
    "웹디자인/홈페이지": "웹개발",
    "웹": "웹개발",
    "그래픽/멀티미디어": "그래픽-멀티미디어",
    "오피스(엑셀/파워포인트)": "오피스",
    "PC/게임/디지털 카메라": "게임-디지털",
    "OS/Networking": "OS-네트워크",
    "e비즈니스/창업": "IT-비즈니스",
    "스마트폰/태블릿/SNS": "모바일",
    "소프트웨어 개발/엔지니어링": "소프트웨어공학",
    "초중고 소프트웨어 교육/코딩": "코딩교육",

    # 02-외국어
    "영어회화": "영어",
    "영어어휘": "영어",
    "영문법": "영어",
    "영어독해": "영어",
    "영어학습법": "영어",
    "영작문": "영어",
    "비즈니스영어": "영어",
    "일본어": "일본어",
    "중국어": "중국어",
    "스페인어": "스페인어",
    "한자": "한자",
    "외국인을 위한 한국어": "한국어",

    # 03-경제-경영
    "기업 경영": "기업경영",
    "재테크/투자": "재테크-투자",
    "트렌드/미래전망": "트렌드-전망",
    "마케팅/세일즈": "마케팅",
    "경제학/경제일반": "경제학",
    "창업/취업/은퇴": "창업",
    "경제발전": "경제학",
    "경력관리": "기업경영",
    "연구개발(R/D)": "기업경영",
    "CEO/비즈니스맨을 위한 능력계발": "기업경영",

    # 04-자기계발
    "시간관리/정보관리": "시간관리-생산성",
    "창의적사고/두뇌계발": "창의력-사고",
    "성공": "성공-처세",
    "기획/보고": "기획-보고",
    "협상/설득/화술": "커뮤니케이션",
    "프레젠테이션/회의": "프레젠테이션",
    "힐링": "힐링",
    "인간관계": "커뮤니케이션",
    "행복론": "힐링",
    "리더십": "성공-처세",
    "취업/진로/유망직업": "성공-처세",

    # 05-인문학
    "심리학/정신분석학": "심리학",
    "책읽기/글쓰기": "글쓰기-독서",
    "교양 인문학": "교양인문",
    "서양철학": "철학",
    "동양철학": "철학",
    "신화/종교학": "종교-신화",
    "기호학/언어학": "언어학",
    "논리와 비판적 사고": "논리-사고",
    "인문 에세이": "교양인문",
    "인류학/고고학": "교양인문",
    "서지/출판": "글쓰기-독서",

    # 06-역사
    "세계사 일반": "세계사",
    "한국근현대사": "한국사",
    "한국사 일반": "한국사",
    "조선사": "한국사",
    "서양사": "서양사",
    "아시아사": "동양사",
    "중국사": "동양사",

    # 07-과학-수학
    "기초과학/교양과학": "교양과학",
    "생명과학": "생명과학",
    "물리학": "물리학",
    "수학": "수학",
    "화학": "화학",
    "천문학": "천문학",
    "뇌과학": "뇌과학",
    "공학": "공학",

    # 08-예술-문화
    "미술": "미술-드로잉",
    "음악": "음악",
    "영화/드라마": "영상",
    "디자인/공예": "디자인",
    "사진": "사진",
    "예술/대중문화의 이해": "예술일반",
    "연극": "공연",
    "만화그리기와 읽기": "만화",
    "건축": "건축",

    # 09-문학
    "영미소설": "소설",
    "세계의 소설": "소설",
    "일본소설": "소설",
    "우리나라 옛글": "고전",
    "과학소설(SF)": "SF소설",
    "한국에세이": "에세이",
    "외국에세이": "에세이",
    "독서에세이": "에세이",
    "문학 잡지": "잡지",

    # 10-사회-시사
    "정치학/외교학/행정학": "정치",
    "한국정치사정/정치사": "정치",
    "사회학": "사회",
    "사회문제": "사회",
    "교육학": "교육",
    "법과 생활": "법률",
    "여성학/젠더": "사회",
    "비평/칼럼": "사회",

    # 11-건강-취미
    "취미기타": "취미",
    "바둑/장기": "보드게임",
    "구기": "스포츠",
    "건강정보": "건강",

    # 12-종교-신비학
    "역학": "역학-점술",
    "가톨릭": "종교",
    "불교": "종교",
    "세계의 종교": "종교",
}

# 현재 폴더 → 미매칭 시 기본 매핑 (fallback)
CURRENT_FOLDER_FALLBACK = {
    "01-프로그래밍-IT": "01-IT-프로그래밍",
    "02-언어학습": "02-외국어",
    "03-비즈니스-자기계발": "03-경제-경영",
    "04-디자인-창작": "08-예술-문화",
    "05-인문학-교양": "05-인문학",
    "06-도구-앱가이드": "01-IT-프로그래밍",
    "07-서예-한문": "08-예술-문화",
    "08-음악-예술": "08-예술-문화",
    "09-신비학-취미": "12-종교-신비학",
    "11-데이터-분석": "01-IT-프로그래밍",
    "12-시사-전망": "10-사회-시사",
    "13-e-books": "09-문학",
    "99-기타-미분류": "99-기타",
}

# 현재 하위폴더 → 새 하위폴더 fallback (알라딘 미매칭 시)
SUBFOLDER_FALLBACK = {
    "01-인공지능-AI": "AI-인공지능",
    "02-웹개발": "웹개발",
    "03-파이썬": "프로그래밍-언어",
    "04-프로그래밍언어": "프로그래밍-언어",
    "05-데이터베이스-백엔드": "컴퓨터공학",
    "06-알고리즘-자료구조": "컴퓨터공학",
    "07-블록체인": "IT-비즈니스",
    "08-프로그래밍기초": "프로그래밍-언어",
    "09-아키텍처-설계": "개발방법론",
    "10-HeadFirst시리즈": "프로그래밍-언어",
    "01-스페인어": "스페인어",
    "02-영어": "영어",
    "03-일본어": "일본어",
    "04-중국어": "중국어",
    "01-비즈니스모델": "기업경영",
    "02-프레젠테이션": "프레젠테이션",
    "03-업무스킬": "기업경영",
    "04-업계지도": "기업경영",
    "05-자기계발": "성공-처세",
    "01-UX-UI디자인": "디자인",
    "02-게임디자인": "디자인",
    "03-스토리텔링": "예술일반",
    "04-그래픽디자인": "디자인",
    "05-웹툰-만화": "만화",
    "01-철학-논리학": "철학",
    "02-역사": "세계사",
    "03-심리학": "심리학",
    "04-과학-수학": "교양과학",
    "05-글쓰기-사고법": "글쓰기-독서",
    "타로": "역학-점술",
    "음악": "음악",
    "한문, 서예": "미술-드로잉",
    "서비스 소셜": "IT-비즈니스",
    "앱, 서비스 가이드": "오피스",
    "캘리버 서재": "소설",
    "쿄시로2030": "소설",
    "01-레고-취미": "취미",
    "02-소프트웨어-도구": "오피스",
    "03-심리-자기계발": "심리학",
    "04-문학-고전": "고전",
    "05-역사-사회": "세계사",
    "06-의학-건강": "건강",
    "07-기타": "기타",
}


def detect_language_from_path(filepath: str) -> str:
    """파일 경로의 하위 폴더명에서 언어 감지."""
    fp = unicodedata.normalize("NFC", filepath).lower()
    if "스페인어" in fp or "espanol" in fp or "español" in fp:
        return "스페인어"
    if "일본어" in fp or "jlpt" in fp or "nihongo" in fp:
        return "일본어"
    if "중국어" in fp or "hsk" in fp or "chinese" in fp:
        return "중국어"
    if "영어" in fp or "english" in fp or "toeic" in fp or "toefl" in fp:
        return "영어"
    return "기타"


def get_current_subfolder(filepath: str) -> str:
    """현재 파일의 하위 폴더명 추출 (NFC 정규화)."""
    try:
        rel = Path(filepath).relative_to(PDF_ROOT)
        parts = rel.parts
        if len(parts) >= 3:  # 대분류/하위폴더/파일명
            return unicodedata.normalize("NFC", parts[1])
    except (ValueError, IndexError):
        pass
    return ""


def get_target_path(aladin_category: str, current_category: str, filepath: str) -> str:
    """알라딘 카테고리 → 새 폴더/하위폴더 경로 결정."""
    current_category = unicodedata.normalize("NFC", current_category)

    main_folder = ""
    sub_folder = ""

    if aladin_category:
        parts = [p.strip() for p in aladin_category.split(">")]
        main_cat = parts[1] if len(parts) >= 2 else ""
        sub_cat = parts[2] if len(parts) >= 3 else ""

        # 대분류 → 메인 폴더
        main_folder = MAIN_FOLDER.get(main_cat, "")

        # 중분류 → 하위 폴더
        if sub_cat and sub_cat in SUB_FOLDER:
            sub_folder = SUB_FOLDER[sub_cat]
        elif main_cat == "외국어":
            sub_folder = detect_language_from_path(filepath)

    # fallback: 메인 폴더
    if not main_folder:
        main_folder = CURRENT_FOLDER_FALLBACK.get(current_category, "99-기타")

    # fallback: 하위 폴더 (기존 하위폴더 매핑)
    if not sub_folder:
        cur_sub = get_current_subfolder(filepath)
        if cur_sub in SUBFOLDER_FALLBACK:
            sub_folder = SUBFOLDER_FALLBACK[cur_sub]
        elif main_folder == "02-외국어":
            sub_folder = detect_language_from_path(filepath)

    if sub_folder:
        return f"{main_folder}/{sub_folder}"
    return main_folder


def plan_migration(dry_run=True):
    """이동 계획 생성. dry_run=True면 CSV만 생성."""
    conn = get_conn()
    books = conn.execute(
        "SELECT id, title, filepath, category, aladin_category FROM books ORDER BY id"
    ).fetchall()
    conn.close()

    moves = []
    for b in books:
        old_path = Path(b["filepath"])
        if not old_path.exists():
            continue

        target_folder = get_target_path(b["aladin_category"], b["category"], b["filepath"])
        new_dir = PDF_ROOT / target_folder
        new_path = new_dir / old_path.name

        # NFC 정규화
        new_path = Path(unicodedata.normalize("NFC", str(new_path)))

        if str(old_path) != str(new_path):
            moves.append({
                "id": b["id"],
                "title": b["title"],
                "old_path": str(old_path),
                "new_path": str(new_path),
                "old_folder": b["category"],
                "new_folder": target_folder,
                "aladin": b["aladin_category"],
            })

    # CSV 백업 저장
    os.makedirs(BACKUP_CSV.parent, exist_ok=True)
    with open(BACKUP_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "title", "old_folder", "new_folder", "old_path", "new_path", "aladin"])
        writer.writeheader()
        writer.writerows(moves)

    print(f"[마이그레이션] 총 {len(books)}권 중 {len(moves)}권 이동 예정")
    print(f"[백업] {BACKUP_CSV}")

    # 새 폴더별 통계
    from collections import Counter
    folder_counts = Counter(m["new_folder"] for m in moves)
    unchanged = len(books) - len(moves)
    print(f"\n이동 없음 (동일 위치): {unchanged}권")
    print("\n새 폴더 구조:")
    for folder, cnt in sorted(folder_counts.items()):
        print(f"  {folder:45s} {cnt:>4}권")

    return moves


def execute_migration(moves: list):
    """실제 파일 이동 + DB 업데이트."""
    conn = get_conn()
    success = 0
    errors = []

    for m in moves:
        old_path = Path(m["old_path"])
        new_path = Path(m["new_path"])

        try:
            # 대상 폴더 생성
            new_path.parent.mkdir(parents=True, exist_ok=True)

            # 파일명 충돌 방지
            if new_path.exists():
                stem = new_path.stem
                suffix = new_path.suffix
                i = 2
                while new_path.exists():
                    new_path = new_path.parent / f"{stem}_{i}{suffix}"
                    i += 1

            # 파일 이동
            shutil.move(str(old_path), str(new_path))

            # DB 업데이트
            new_category = m["new_folder"].split("/")[0]  # 최상위 폴더명
            conn.execute(
                "UPDATE books SET filepath = ?, category = ? WHERE id = ?",
                (str(new_path), new_category, m["id"])
            )
            success += 1

        except Exception as e:
            errors.append(f"[오류] {m['title']}: {e}")

    conn.commit()
    conn.close()

    print(f"\n[완료] {success}/{len(moves)}권 이동 성공")
    if errors:
        print(f"[오류] {len(errors)}건:")
        for e in errors:
            print(f"  {e}")


if __name__ == "__main__":
    import sys

    if "--execute" in sys.argv:
        print("=== 실행 모드 ===")
        moves = plan_migration(dry_run=False)
        if moves:
            execute_migration(moves)
    else:
        print("=== 시뮬레이션 모드 (--execute 로 실행) ===")
        plan_migration(dry_run=True)
