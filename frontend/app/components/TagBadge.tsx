"use client";

interface Props {
  tag: string;
  onClick?: () => void;
  onRemove?: () => void;
  selected?: boolean;
}

// 태그별 색상
const TAG_COLORS: Record<string, string> = {
  "AI-ChatGPT":      "bg-violet-600/80 text-violet-100",
  "프로그래밍":       "bg-blue-600/80 text-blue-100",
  "파이썬":          "bg-blue-500/80 text-blue-100",
  "웹개발":          "bg-cyan-600/80 text-cyan-100",
  "데이터분석":       "bg-teal-600/80 text-teal-100",
  "업계지도":        "bg-amber-600/80 text-amber-100",
  "경제-투자":       "bg-yellow-600/80 text-yellow-100",
  "영어":            "bg-green-600/80 text-green-100",
  "일본어":          "bg-green-500/80 text-green-100",
  "중국어":          "bg-emerald-600/80 text-emerald-100",
  "스페인어":        "bg-lime-600/80 text-lime-100",
  "비즈니스":        "bg-orange-600/80 text-orange-100",
  "마케팅":          "bg-orange-500/80 text-orange-100",
  "자기계발":        "bg-rose-500/80 text-rose-100",
  "생산성":          "bg-rose-600/80 text-rose-100",
  "글쓰기-사고법":   "bg-pink-600/80 text-pink-100",
  "디자인-UX":       "bg-purple-600/80 text-purple-100",
  "창작-드로잉":     "bg-purple-500/80 text-purple-100",
  "스토리-시나리오": "bg-indigo-600/80 text-indigo-100",
  "철학-사상":       "bg-slate-500/80 text-slate-100",
  "역사":            "bg-stone-600/80 text-stone-100",
  "심리학":          "bg-red-500/80 text-red-100",
  "과학-수학":       "bg-sky-600/80 text-sky-100",
  "음악":            "bg-fuchsia-600/80 text-fuchsia-100",
  "서예-한문":       "bg-zinc-600/80 text-zinc-100",
  "타로":            "bg-violet-800/80 text-violet-100",
  "신비학":          "bg-violet-900/80 text-violet-200",
  "레고":            "bg-red-600/80 text-red-100",
  "게임-보드게임":   "bg-green-700/80 text-green-100",
  "사진-영상":       "bg-neutral-600/80 text-neutral-100",
  "시사-사회":       "bg-gray-600/80 text-gray-100",
  "건강-의학":       "bg-teal-700/80 text-teal-100",
  "HeadFirst시리즈": "bg-orange-700/80 text-orange-100",
};

const DEFAULT_COLOR = "bg-slate-600/80 text-slate-100";

export default function TagBadge({ tag, onClick, onRemove, selected }: Props) {
  const color = TAG_COLORS[tag] || DEFAULT_COLOR;

  return (
    <span
      className={`
        inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium
        ${color}
        ${onClick ? "cursor-pointer hover:opacity-80 transition-opacity" : ""}
        ${selected ? "ring-2 ring-white/50" : ""}
      `}
      onClick={onClick}
    >
      #{tag}
      {onRemove && (
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          className="ml-0.5 opacity-70 hover:opacity-100"
        >
          ✕
        </button>
      )}
    </span>
  );
}
