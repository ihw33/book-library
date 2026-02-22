"""
알라딘 API 연동
- ISBN 또는 제목으로 검색
- categoryName → 태그 자동 매핑
- 표지 이미지 URL 제공
"""

import httpx
import os
import unicodedata
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

ALADIN_KEY = os.getenv("ALADIN_KEY", "")
ALADIN_SEARCH = "http://www.aladin.co.kr/ttb/api/ItemSearch.aspx"
ALADIN_LOOKUP = "http://www.aladin.co.kr/ttb/api/ItemLookUp.aspx"

# ─── 알라딘 대분류 → 태그 매핑 ──────────────────────────────
# 알라딘 categoryName 형식: "국내도서>대분류>중분류>소분류"

CATEGORY_TAG_MAP = {
    # 대분류 키워드 → 태그들
    "컴퓨터/모바일": ["프로그래밍"],
    "컴퓨터/IT": ["프로그래밍"],
    "프로그래밍": ["프로그래밍"],
    "인공지능": ["AI-ChatGPT"],
    "웹프로그래밍": ["웹개발"],
    "웹개발": ["웹개발"],
    "데이터베이스": ["프로그래밍"],
    "머신러닝": ["AI-ChatGPT", "데이터분석"],
    "딥러닝": ["AI-ChatGPT", "데이터분석"],

    "경제경영": ["비즈니스"],
    "경영일반": ["비즈니스"],
    "마케팅": ["마케팅"],
    "재테크": ["경제-투자"],
    "투자": ["경제-투자"],
    "주식": ["경제-투자"],
    "창업": ["비즈니스"],

    "자기계발": ["자기계발"],
    "성공/처세": ["자기계발"],
    "인간관계": ["자기계발"],
    "시간관리": ["생산성"],

    "인문학": ["인문교양"],
    "철학": ["철학-사상"],
    "심리학": ["심리학"],
    "심리": ["심리학"],
    "역사": ["역사"],
    "한국사": ["역사"],
    "세계사": ["역사"],
    "정치/사회": ["시사-사회"],
    "사회과학": ["시사-사회"],

    "과학": ["과학-수학"],
    "수학": ["과학-수학"],
    "물리학": ["과학-수학"],
    "생명과학": ["과학-수학"],

    "외국어": [],  # 세부 분류로 처리
    "영어": ["영어"],
    "일본어": ["일본어"],
    "중국어": ["중국어"],
    "스페인어": ["스페인어"],

    "예술/대중문화": ["음악"],
    "음악": ["음악"],
    "미술": ["창작-드로잉"],
    "디자인": ["디자인-UX"],
    "사진": ["사진-영상"],
    "영화": ["사진-영상"],

    "만화": ["창작-드로잉"],
    "소설/시/희곡": ["문학"],
    "소설": ["문학"],
    "에세이": ["문학"],
    "시": ["문학"],

    "건강/취미": ["건강-의학"],
    "건강": ["건강-의학"],
    "의학": ["건강-의학"],
    "취미": [],  # 세부 분류로 처리
    "게임": ["게임-보드게임"],

    "종교/역학": ["신비학"],
    "역학": ["신비학"],
    "점술": ["타로"],
}


def parse_aladin_category(category_name: str) -> list[str]:
    """알라딘 categoryName 문자열에서 태그 목록 추출.
    예: '국내도서>인문학>심리학>심리학 일반' → ['인문교양', '심리학']
    """
    if not category_name:
        return []

    tags = set()
    # '>' 로 분리된 각 수준을 모두 검사
    parts = [p.strip() for p in category_name.split(">")]

    for part in parts:
        # 정확 매칭
        if part in CATEGORY_TAG_MAP:
            tags.update(CATEGORY_TAG_MAP[part])
        # 부분 매칭 (키워드 포함)
        else:
            part_lower = part.lower()
            for key, tag_list in CATEGORY_TAG_MAP.items():
                if key.lower() in part_lower or part_lower in key.lower():
                    tags.update(tag_list)
                    break

    return sorted(tags)


async def search_aladin(client: httpx.AsyncClient, isbn: str = "", title: str = "") -> dict:
    """알라딘 API로 책 정보 검색. ISBN 우선, 없으면 제목 검색."""
    if not ALADIN_KEY:
        return {}

    try:
        if isbn and len(isbn) >= 10:
            # ISBN 검색 (ItemLookUp)
            r = await client.get(ALADIN_LOOKUP, params={
                "ttbkey": ALADIN_KEY,
                "itemIdType": "ISBN13" if len(isbn) == 13 else "ISBN",
                "ItemId": isbn,
                "output": "js",
                "Version": "20131101",
                "Cover": "Big",
            }, timeout=10)
        elif title:
            # 제목 검색
            query = unicodedata.normalize("NFC", title)
            r = await client.get(ALADIN_SEARCH, params={
                "ttbkey": ALADIN_KEY,
                "Query": query,
                "QueryType": "Title",
                "MaxResults": 1,
                "output": "js",
                "Version": "20131101",
                "Cover": "Big",
            }, timeout=10)
        else:
            return {}

        data = r.json()
        items = data.get("item", [])
        if not items:
            return {}

        item = items[0]
        category_name = item.get("categoryName", "")

        return {
            "title_api": item.get("title", ""),
            "author": item.get("author", "").split(" (")[0],  # "(지은이)" 제거
            "publisher": item.get("publisher", ""),
            "description": item.get("description", "")[:500],
            "cover_url": item.get("cover", ""),
            "isbn": item.get("isbn13", "") or item.get("isbn", ""),
            "category_name": category_name,
            "category_tags": parse_aladin_category(category_name),
        }
    except Exception as e:
        return {}
