"use client";

interface BaziChipProps {
  status: string; // "executing" | "complete" | "inProgress"
}

export function BaziChip({ status }: BaziChipProps) {
  const isLoading = status !== "complete";

  return (
    <div className="animate-chip-enter my-2">
      <div
        className={`
          relative overflow-hidden rounded-xl border
          transition-all duration-500 ease-out
          ${isLoading
            ? "border-purple-300/60 bg-gradient-to-r from-purple-50 to-indigo-50/50"
            : "border-purple-200/40 bg-purple-50/50"
          }
        `}
      >
        {isLoading && (
          <div className="absolute inset-0 shimmer-block pointer-events-none" />
        )}

        <div className="relative flex items-center gap-3 px-4 py-3">
          {/* Icon: yin-yang / compass */}
          <div
            className={`
              flex-shrink-0 flex items-center justify-center
              w-8 h-8 rounded-lg
              transition-all duration-500
              ${isLoading
                ? "bg-purple-400/15 text-purple-600"
                : "bg-purple-500/10 text-purple-500"
              }
            `}
          >
            {isLoading ? (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="animate-spin" style={{ animationDuration: "2s" }}>
                <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="28" strokeDashoffset="8" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.3" />
                <path d="M8 1.5A6.5 6.5 0 0 1 8 14.5C8 11.2 5.5 8 8 8s0-3.2 0-6.5z" fill="currentColor" opacity="0.2" />
                <circle cx="8" cy="5" r="1.2" fill="currentColor" />
                <circle cx="8" cy="11" r="1.2" stroke="currentColor" strokeWidth="0.8" fill="none" />
              </svg>
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span
                className="text-[13px] font-medium"
                style={{ color: isLoading ? "#6d28d9" : "#5b21b6" }}
              >
                {isLoading ? "正在查阅命盘" : "命盘查询完成"}
              </span>

              {isLoading && (
                <span className="flex gap-0.5">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="pulse-dot inline-block w-1 h-1 rounded-full bg-purple-400"
                    />
                  ))}
                </span>
              )}
            </div>

            <p className="text-[12px] mt-0.5 truncate" style={{ color: "#8c7e6f" }}>
              {isLoading ? "八字 / 流日 / 体质分析" : "已获取八字与今日流日信息"}
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
