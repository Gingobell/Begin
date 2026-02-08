"use client";

interface DiarySearchChipProps {
  query?: string;
  maxResults?: number;
  status: string; // "executing" | "complete" | "inProgress"
}

export function DiarySearchChip({ query, maxResults, status }: DiarySearchChipProps) {
  const isSearching = status !== "complete";

  return (
    <div className="animate-chip-enter my-2">
      <div
        className={`
          relative overflow-hidden rounded-xl border
          transition-all duration-500 ease-out
          ${isSearching
            ? "border-fortune-300/60 bg-gradient-to-r from-fortune-50 to-orange-50/50"
            : "border-fortune-200/40 bg-fortune-50/50"
          }
        `}
      >
        {/* Shimmer overlay while searching */}
        {isSearching && (
          <div className="absolute inset-0 shimmer pointer-events-none" />
        )}

        <div className="relative flex items-center gap-3 px-4 py-3">
          {/* Icon */}
          <div
            className={`
              flex-shrink-0 flex items-center justify-center
              w-8 h-8 rounded-lg
              transition-all duration-500
              ${isSearching
                ? "bg-fortune-400/15 text-fortune-600"
                : "bg-fortune-500/10 text-fortune-500"
              }
            `}
          >
            {isSearching ? (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="animate-spin" style={{ animationDuration: "2s" }}>
                <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="28" strokeDashoffset="8" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3 2.5h10a1 1 0 011 1v9a1 1 0 01-1 1H3a1 1 0 01-1-1v-9a1 1 0 011-1z" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
                <path d="M5 5.5h6M5 8h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
              </svg>
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span
                className="text-[13px] font-medium"
                style={{ color: isSearching ? "#b9490a" : "#933a10" }}
              >
                {isSearching ? "正在翻阅日记" : "日记检索完成"}
              </span>

              {isSearching && (
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

            {query && (
              <p className="text-[12px] mt-0.5 truncate" style={{ color: "#8c7e6f" }}>
                关键词：
                <span className="text-fortune-700 font-medium">{query}</span>
                {maxResults && maxResults !== 5 && (
                  <span className="ml-1.5 opacity-60">· 最多{maxResults}条</span>
                )}
              </p>
            )}
          </div>

          {/* Status indicator */}
          {!isSearching && (
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
