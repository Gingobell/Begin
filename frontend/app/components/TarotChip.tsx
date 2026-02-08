"use client";

interface TarotChipProps {
  status: string; // "executing" | "complete" | "inProgress"
}

export function TarotChip({ status }: TarotChipProps) {
  const isLoading = status !== "complete";

  return (
    <div className="animate-chip-enter my-2">
      <div
        className={`
          relative overflow-hidden rounded-xl border
          transition-all duration-500 ease-out
          ${isLoading
            ? "border-fortune-300/60 bg-gradient-to-r from-amber-50 to-fortune-50/50"
            : "border-fortune-200/40 bg-fortune-50/50"
          }
        `}
      >
        {isLoading && (
          <div className="absolute inset-0 shimmer-block pointer-events-none" />
        )}

        <div className="relative flex items-center gap-3 px-4 py-3">
          {/* Icon: tarot card */}
          <div
            className={`
              flex-shrink-0 flex items-center justify-center
              w-8 h-8 rounded-lg
              transition-all duration-500
              ${isLoading
                ? "bg-fortune-400/15 text-fortune-600"
                : "bg-fortune-500/10 text-fortune-500"
              }
            `}
          >
            {isLoading ? (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="animate-spin" style={{ animationDuration: "2s" }}>
                <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="28" strokeDashoffset="8" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <rect x="3" y="1.5" width="10" height="13" rx="1.5" stroke="currentColor" strokeWidth="1.3" />
                <path d="M8 5l1.5 2.5H6.5L8 5z" stroke="currentColor" strokeWidth="1" strokeLinejoin="round" />
                <circle cx="8" cy="10.5" r="1" stroke="currentColor" strokeWidth="0.8" />
              </svg>
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span
                className="text-[13px] font-medium"
                style={{ color: isLoading ? "#b9490a" : "#933a10" }}
              >
                {isLoading ? "正在翻阅塔罗牌" : "塔罗查询完成"}
              </span>

              {isLoading && (
                <span className="flex gap-0.5">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="pulse-dot inline-block w-1 h-1 rounded-full bg-fortune-400"
                    />
                  ))}
                </span>
              )}
            </div>

            <p className="text-[12px] mt-0.5 truncate" style={{ color: "#8c7e6f" }}>
              {isLoading ? "今日塔罗 / 牌义解读" : "已获取今日塔罗牌信息"}
            </p>
          </div>

          {/* Status indicator */}
          {!isLoading && (
            <div className="flex-shrink-0">
              <div className="flex items-center justify-center w-5 h-5 rounded-full bg-emerald-100">
                <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                  <path d="M2 5.5L4 7.5L8 3" stroke="#059669" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
