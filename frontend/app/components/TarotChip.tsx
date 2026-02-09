"use client";

import { BaseChip } from "./BaseChip";

interface TarotChipProps {
  status: string;
}

const colorScheme = {
  border: "border border-fortune-300/60",
  borderDone: "border border-fortune-200/40",
  bg: "bg-fortune-50/70",
  bgDone: "bg-fortune-50/50",
  iconBg: "bg-fortune-400/15",
  iconBgDone: "bg-fortune-500/10",
  iconText: "text-fortune-600",
  iconTextDone: "text-fortune-500",
  labelActive: "#b9490a",
  labelDone: "#933a10",
  dot: "bg-fortune-400",
};

export function TarotChip({ status }: TarotChipProps) {
  const isActive = status !== "complete";

  return (
    <BaseChip
      isActive={isActive}
      activeLabel="正在翻阅塔罗牌"
      completeLabel="塔罗查询完成"
      colorScheme={colorScheme}
      subtitle={isActive ? "今日塔罗 / 牌义解读" : "已获取今日塔罗牌信息"}
      activeIcon={
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none" className="animate-spin" style={{ animationDuration: "2s" }}>
          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="28" strokeDashoffset="8" />
        </svg>
      }
      completeIcon={
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
          <rect x="3" y="1.5" width="10" height="13" rx="1.5" stroke="currentColor" strokeWidth="1.3" />
          <path d="M8 5l1.5 2.5H6.5L8 5z" stroke="currentColor" strokeWidth="1" strokeLinejoin="round" />
          <circle cx="8" cy="10.5" r="1" stroke="currentColor" strokeWidth="0.8" />
        </svg>
      }
    />
  );
}
