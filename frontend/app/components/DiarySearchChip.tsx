"use client";

import { BaseChip } from "./BaseChip";
import { useTranslation } from "../i18n";

interface DiarySearchChipProps {
  query?: string;
  maxResults?: number;
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

export function DiarySearchChip({ query, maxResults, status }: DiarySearchChipProps) {
  const { t } = useTranslation();
  const isActive = status !== "complete";

  return (
    <BaseChip
      isActive={isActive}
      activeLabel={t("chips.diary.active")}
      completeLabel={t("chips.diary.complete")}
      colorScheme={colorScheme}
      subtitle={
        query ? (
          <>
            {t("chips.diary.keyword")}: <span className="text-fortune-700 font-medium">{query}</span>
            {maxResults && maxResults !== 5 && (
              <span className="ml-1.5 opacity-60">· {t("chips.diary.maxResults").replace("{count}", String(maxResults))}</span>
            )}
          </>
        ) : undefined
      }
      activeIcon={
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none" className="animate-spin" style={{ animationDuration: "2s" }}>
          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="28" strokeDashoffset="8" />
        </svg>
      }
      completeIcon={
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
          <path d="M3 2.5h10a1 1 0 011 1v9a1 1 0 01-1 1H3a1 1 0 01-1-1v-9a1 1 0 011-1z" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
          <path d="M5 5.5h6M5 8h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
      }
    />
  );
}
