"use client";

import { BaseChip } from "./BaseChip";

interface BaziChipProps {
  status: string;
}

const colorScheme = {
  border: "border border-purple-300/60",
  borderDone: "border border-purple-200/40",
  bg: "bg-purple-50/70",
  bgDone: "bg-purple-50/50",
  iconBg: "bg-purple-400/15",
  iconBgDone: "bg-purple-500/10",
  iconText: "text-purple-600",
  iconTextDone: "text-purple-500",
  labelActive: "#6d28d9",
  labelDone: "#5b21b6",
  dot: "bg-purple-400",
};

export function BaziChip({ status }: BaziChipProps) {
  const isActive = status !== "complete";

  return (
    <BaseChip
      isActive={isActive}
      activeLabel="正在查阅命盘"
      completeLabel="命盘查询完成"
      colorScheme={colorScheme}
      subtitle={isActive ? "八字 / 流日 / 体质分析" : "已获取八字与今日流日信息"}
      activeIcon={
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none" className="animate-spin" style={{ animationDuration: "2s" }}>
          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="28" strokeDashoffset="8" />
        </svg>
      }
      completeIcon={
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
          <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.3" />
          <path d="M8 1.5A6.5 6.5 0 0 1 8 14.5C8 11.2 5.5 8 8 8s0-3.2 0-6.5z" fill="currentColor" opacity="0.2" />
          <circle cx="8" cy="5" r="1.2" fill="currentColor" />
          <circle cx="8" cy="11" r="1.2" stroke="currentColor" strokeWidth="0.8" fill="none" />
        </svg>
      }
    />
  );
}
