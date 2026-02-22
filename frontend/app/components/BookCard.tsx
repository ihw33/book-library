"use client";

import { useState } from "react";
import TagBadge from "./TagBadge";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002";

// 카테고리별 배경색 (표지 없을 때)
const CATEGORY_COLORS: Record<string, string> = {
  "01-프로그래밍-IT": "from-blue-800 to-blue-600",
  "02-언어학습": "from-green-800 to-green-600",
  "03-비즈니스-자기계발": "from-orange-800 to-orange-600",
  "04-디자인-창작": "from-purple-800 to-purple-600",
  "05-인문학-교양": "from-rose-800 to-rose-600",
  "06-도구-앱가이드": "from-cyan-800 to-cyan-600",
  "07-서예-한문": "from-amber-800 to-amber-600",
  "08-음악-예술": "from-pink-800 to-pink-600",
  "09-신비학-취미": "from-violet-800 to-violet-600",
  "11-데이터-분석": "from-teal-800 to-teal-600",
  "12-시사-전망": "from-red-800 to-red-600",
  "13-e-books": "from-indigo-800 to-indigo-600",
  "99-기타-미분류": "from-slate-700 to-slate-600",
};

interface Book {
  id: number;
  title: string;
  author: string;
  category: string;
  cover_url: string;
  cover_local: string;
  page_count: number;
  filesize: number;
  tags: string[];
}

interface Props {
  book: Book;
  isMobile: boolean;
  onTagClick?: (tag: string) => void;
}

export default function BookCard({ book, isMobile, onTagClick }: Props) {
  const [imgError, setImgError] = useState(false);
  const coverUrl = `${API}/books/${book.id}/cover`;
  const gradientClass = CATEGORY_COLORS[book.category] || "from-slate-700 to-slate-600";

  const handleClick = async () => {
    if (isMobile) {
      // 모바일: 새 탭으로 PDF 스트리밍
      window.open(`${API}/books/${book.id}/stream`, "_blank");
    } else {
      // 데스크톱: macOS 기본 뷰어로 열기
      await fetch(`${API}/books/${book.id}/open`, { method: "POST" });
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes > 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024 / 1024).toFixed(1)}GB`;
    if (bytes > 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(0)}MB`;
    return `${(bytes / 1024).toFixed(0)}KB`;
  };

  return (
    <div
      onClick={handleClick}
      className="group cursor-pointer rounded-xl overflow-hidden bg-slate-800 hover:bg-slate-700 transition-all duration-200 hover:scale-[1.02] hover:shadow-2xl active:scale-95"
    >
      {/* 표지 */}
      <div className="relative aspect-[3/4] overflow-hidden">
        {!imgError ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={coverUrl}
            alt={book.title}
            className="w-full h-full object-cover"
            onError={() => setImgError(true)}
            loading="lazy"
          />
        ) : (
          <div className={`w-full h-full bg-gradient-to-b ${gradientClass} flex flex-col items-center justify-center p-3`}>
            <div className="text-4xl mb-2">📖</div>
            <p className="text-white text-xs text-center font-medium line-clamp-2 leading-tight">
              {book.title}
            </p>
          </div>
        )}
        {/* 페이지 수 배지 */}
        {book.page_count > 0 && (
          <div className="absolute bottom-2 right-2 bg-black/70 text-white text-xs px-1.5 py-0.5 rounded">
            {book.page_count}p
          </div>
        )}
      </div>

      {/* 정보 */}
      <div className="p-2.5">
        <p className="text-sm font-medium text-slate-100 line-clamp-2 leading-tight mb-1">
          {book.title}
        </p>
        {book.author && (
          <p className="text-xs text-slate-400 truncate">{book.author}</p>
        )}
        <div className="flex items-center justify-between mt-1.5">
          <span className="text-xs text-slate-500 truncate">
            {book.category.replace(/^\d+-/, "")}
          </span>
          <span className="text-xs text-slate-600">{formatSize(book.filesize)}</span>
        </div>

        {/* 태그 */}
        {book.tags && book.tags.length > 0 && (
          <div
            className="flex flex-wrap gap-1 mt-2"
            onClick={(e) => e.stopPropagation()}
          >
            {book.tags.slice(0, 3).map((tag) => (
              <TagBadge
                key={tag}
                tag={tag}
                onClick={onTagClick ? () => onTagClick(tag) : undefined}
              />
            ))}
            {book.tags.length > 3 && (
              <span className="text-xs text-slate-500 self-center">+{book.tags.length - 3}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
