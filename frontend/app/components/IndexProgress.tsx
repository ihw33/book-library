"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8002";

interface IndexState {
  running: boolean;
  current: number;
  total: number;
  current_title: string;
  done: boolean;
  error: string;
}

interface Props {
  onComplete?: () => void;
}

export default function IndexProgress({ onComplete }: Props) {
  const [state, setState] = useState<IndexState | null>(null);
  const [show, setShow] = useState(false);

  useEffect(() => {
    // 인덱싱 상태 확인
    fetch(`${API}/admin/status`)
      .then((r) => r.json())
      .then((s: IndexState) => {
        if (s.running || s.total === 0) setShow(true);
        setState(s);
        if (s.running) startSSE();
      })
      .catch(() => {});
  }, []);

  const startSSE = () => {
    const es = new EventSource(`${API}/admin/status/stream`);
    es.onmessage = (e) => {
      const s: IndexState = JSON.parse(e.data);
      setState(s);
      if (!s.running) {
        es.close();
        if (s.done) onComplete?.();
      }
    };
    es.onerror = () => es.close();
  };

  const startIndex = async () => {
    await fetch(`${API}/admin/reindex`, { method: "POST" });
    startSSE();
    setShow(true);
  };

  if (!show) {
    return (
      <button
        onClick={startIndex}
        className="text-xs text-slate-500 hover:text-slate-300 underline"
      >
        인덱싱 시작
      </button>
    );
  }

  if (!state) return null;

  const pct = state.total > 0 ? Math.round((state.current / state.total) * 100) : 0;

  return (
    <div className="bg-slate-800 rounded-xl p-4 mb-4 border border-slate-700">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-slate-300">
          {state.running ? "📚 인덱싱 중..." : state.done ? "✅ 인덱싱 완료" : "대기 중"}
        </span>
        <span className="text-xs text-slate-500">
          {state.current} / {state.total} ({pct}%)
        </span>
      </div>
      <div className="w-full bg-slate-700 rounded-full h-2 mb-2">
        <div
          className="bg-blue-500 h-2 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      {state.current_title && (
        <p className="text-xs text-slate-500 truncate">{state.current_title}</p>
      )}
      {state.error && (
        <p className="text-xs text-red-400 mt-1">{state.error}</p>
      )}
    </div>
  );
}
