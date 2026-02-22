"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import BookCard from "./components/BookCard";
import IndexProgress from "./components/IndexProgress";
import TagBadge from "./components/TagBadge";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002";

interface Book {
  id: number;
  title: string;
  author: string;
  category: string;
  cover_url: string;
  cover_local: string;
  page_count: number;
  filesize: number;
}

interface Category {
  category: string;
  count: number;
}

export default function Home() {
  const [books, setBooks] = useState<Book[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);

  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedTag, setSelectedTag] = useState("");
  const [tags, setTags] = useState<{ name: string; count: number }[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarMode, setSidebarMode] = useState<"folder" | "tag">("folder");
  const [isMobile, setIsMobile] = useState(false);

  const observerRef = useRef<IntersectionObserver | null>(null);
  const loadMoreRef = useRef<HTMLDivElement | null>(null);

  // 모바일 감지
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  // 검색어 debounce
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(t);
  }, [query]);

  // 카테고리 + 태그 목록
  useEffect(() => {
    fetch(`${API}/categories`).then((r) => r.json()).then(setCategories).catch(() => {});
    fetch(`${API}/tags`).then((r) => r.json()).then(setTags).catch(() => {});
  }, []);

  // 도서 목록 로드
  const loadBooks = useCallback(async (reset = false) => {
    if (loading) return;
    setLoading(true);
    const p = reset ? 1 : page;
    try {
      const params = new URLSearchParams({
        q: debouncedQuery,
        category: selectedCategory,
        tag: selectedTag,
        page: String(p),
        size: "40",
      });
      const r = await fetch(`${API}/books?${params}`);
      const data = await r.json();
      setBooks((prev) => (reset ? data.items : [...prev, ...data.items]));
      setTotal(data.total);
      setHasMore(p < data.pages);
      setPage(p + 1);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [debouncedQuery, selectedCategory, page, loading]);

  // 검색어/카테고리/태그 변경 시 리셋
  useEffect(() => {
    setPage(1);
    setBooks([]);
    setHasMore(true);
    loadBooks(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQuery, selectedCategory, selectedTag]);

  // 무한 스크롤
  useEffect(() => {
    if (observerRef.current) observerRef.current.disconnect();
    observerRef.current = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasMore && !loading) {
        loadBooks();
      }
    });
    if (loadMoreRef.current) observerRef.current.observe(loadMoreRef.current);
    return () => observerRef.current?.disconnect();
  }, [hasMore, loading, loadBooks]);

  const categoryLabel = (cat: string) => cat.replace(/^\d+-/, "");

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ── 사이드바 (데스크톱: 고정 / 모바일: 슬라이드) ── */}
      <>
        {/* 모바일 오버레이 */}
        {sidebarOpen && isMobile && (
          <div
            className="fixed inset-0 bg-black/60 z-20 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
        <aside
          className={`
            fixed md:relative z-30 h-full w-64 bg-slate-800 border-r border-slate-700
            flex flex-col transition-transform duration-300
            ${sidebarOpen || !isMobile ? "translate-x-0" : "-translate-x-full"}
            md:translate-x-0
          `}
        >
          <div className="p-4 border-b border-slate-700">
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
              📚 내 도서관
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">{total}권</p>
            {/* 폴더 / 태그 탭 */}
            <div className="flex mt-3 bg-slate-700 rounded-lg p-0.5">
              <button
                onClick={() => setSidebarMode("folder")}
                className={`flex-1 text-xs py-1.5 rounded-md transition-colors ${
                  sidebarMode === "folder" ? "bg-slate-500 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                📁 폴더
              </button>
              <button
                onClick={() => setSidebarMode("tag")}
                className={`flex-1 text-xs py-1.5 rounded-md transition-colors ${
                  sidebarMode === "tag" ? "bg-slate-500 text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                🏷 태그
              </button>
            </div>
          </div>

          <nav className="flex-1 overflow-y-auto p-3">
            {sidebarMode === "folder" ? (
              <>
                {/* 전체 */}
                <button
                  onClick={() => { setSelectedCategory(""); setSelectedTag(""); setSidebarOpen(false); }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-1 transition-colors
                    ${!selectedCategory && !selectedTag ? "bg-blue-600 text-white" : "text-slate-300 hover:bg-slate-700"}`}
                >
                  🗂 전체 ({total})
                </button>

                <p className="text-xs text-slate-500 px-3 mt-3 mb-1">카테고리</p>
                {categories.map((c) => (
                  <button
                    key={c.category}
                    onClick={() => { setSelectedCategory(c.category); setSelectedTag(""); setSidebarOpen(false); }}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-0.5 transition-colors flex justify-between
                      ${selectedCategory === c.category ? "bg-blue-600 text-white" : "text-slate-300 hover:bg-slate-700"}`}
                  >
                    <span className="truncate">{categoryLabel(c.category)}</span>
                    <span className="text-xs opacity-70 ml-2 shrink-0">{c.count}</span>
                  </button>
                ))}
              </>
            ) : (
              <>
                {/* 태그 전체 */}
                <button
                  onClick={() => { setSelectedTag(""); setSelectedCategory(""); setSidebarOpen(false); }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-1 transition-colors
                    ${!selectedTag && !selectedCategory ? "bg-blue-600 text-white" : "text-slate-300 hover:bg-slate-700"}`}
                >
                  🏷 전체 태그
                </button>

                <p className="text-xs text-slate-500 px-3 mt-3 mb-2">테마별 탐색</p>
                <div className="flex flex-wrap gap-1.5 px-1">
                  {tags.map((t) => (
                    <button
                      key={t.name}
                      onClick={() => { setSelectedTag(t.name); setSelectedCategory(""); setSidebarOpen(false); }}
                      className="text-left"
                    >
                      <TagBadge
                        tag={t.name}
                        selected={selectedTag === t.name}
                      />
                      <span className="text-xs text-slate-500 ml-1">{t.count}</span>
                    </button>
                  ))}
                </div>
              </>
            )}
          </nav>

          <div className="p-3 border-t border-slate-700">
            <IndexProgress onComplete={() => { setPage(1); setBooks([]); loadBooks(true); }} />
          </div>
        </aside>
      </>

      {/* ── 메인 콘텐츠 ── */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* 헤더 */}
        <header className="bg-slate-800/80 backdrop-blur border-b border-slate-700 p-3 flex items-center gap-3 sticky top-0 z-10">
          {/* 모바일 햄버거 */}
          <button
            className="md:hidden p-2 rounded-lg hover:bg-slate-700 text-slate-400"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            ☰
          </button>

          {/* 검색창 */}
          <div className="flex-1 relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">🔍</span>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="제목, 저자, 내용 검색..."
              className="w-full bg-slate-700 border border-slate-600 rounded-xl pl-9 pr-4 py-2.5
                         text-sm text-slate-100 placeholder-slate-500
                         focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* 선택된 필터 표시 */}
          {(selectedCategory || selectedTag) && (
            <button
              onClick={() => { setSelectedCategory(""); setSelectedTag(""); }}
              className="flex items-center gap-1 bg-blue-600 text-white text-xs px-3 py-1.5 rounded-full whitespace-nowrap"
            >
              {selectedTag ? `#${selectedTag}` : categoryLabel(selectedCategory)} ✕
            </button>
          )}
        </header>

        {/* 그리드 */}
        <div className="flex-1 overflow-y-auto p-4">
          {books.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center h-64 text-slate-500">
              <div className="text-5xl mb-4">📭</div>
              <p className="text-lg">책이 없습니다</p>
              <p className="text-sm mt-1">
                {total === 0 ? "먼저 인덱싱을 실행해주세요" : "검색 결과가 없습니다"}
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
            {books.map((book) => (
              <BookCard
                key={book.id}
                book={book}
                isMobile={isMobile}
                onTagClick={(tag) => { setSelectedTag(tag); setSelectedCategory(""); setSidebarMode("tag"); }}
              />
            ))}
          </div>

          {/* 무한 스크롤 트리거 */}
          <div ref={loadMoreRef} className="h-16 flex items-center justify-center">
            {loading && (
              <div className="text-slate-500 text-sm animate-pulse">불러오는 중...</div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
