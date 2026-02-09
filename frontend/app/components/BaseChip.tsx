"use client";

import { ReactNode } from "react";

interface BaseChipProps {
  isActive: boolean;
  activeLabel: string;
  completeLabel: string;
  subtitle?: ReactNode;
  activeIcon: ReactNode;
  completeIcon: ReactNode;
  colorScheme: {
    border: string;        // active border
    borderDone: string;    // complete border
    bg: string;            // active bg
    bgDone: string;        // complete bg
    iconBg: string;        // active icon bg
    iconBgDone: string;    // complete icon bg
    iconText: string;      // active icon color
    iconTextDone: string;  // complete icon color
    labelActive: string;   // active label color
    labelDone: string;     // complete label color
    dot: string;           // pulse dot color
  };
}

export function BaseChip({
  isActive,
  activeLabel,
  completeLabel,
  subtitle,
  activeIcon,
  completeIcon,
  colorScheme: c,
}: BaseChipProps) {
  return (
    <div className="animate-chip-enter my-1">
      <div
        className={`
          relative overflow-hidden rounded-2xl
          transition-all duration-500 ease-out
          ${isActive ? `${c.border} ${c.bg}` : `${c.borderDone} ${c.bgDone}`}
        `}
      >
        {isActive && (
          <div className="absolute inset-0 shimmer-block pointer-events-none" />
        )}

        <div className="relative flex items-center gap-2.5 px-3 py-2">
          {/* Icon */}
          <div
            className={`
              flex-shrink-0 flex items-center justify-center
              w-6 h-6 rounded-full
              transition-all duration-500
              ${isActive ? `${c.iconBg} ${c.iconText}` : `${c.iconBgDone} ${c.iconTextDone}`}
            `}
          >
            {isActive ? activeIcon : completeIcon}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <span
                className="text-[12px] font-medium"
                style={{ color: isActive ? c.labelActive : c.labelDone }}
              >
                {isActive ? activeLabel : completeLabel}
              </span>

              {isActive && (
                <span className="flex gap-0.5">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className={`pulse-dot inline-block w-0.5 h-0.5 rounded-full ${c.dot}`}
                    />
                  ))}
                </span>
              )}
            </div>

            {subtitle && (
              <p className="text-[11px] mt-0.5 truncate" style={{ color: "#8c7e6f" }}>
                {subtitle}
              </p>
            )}
          </div>

          {/* Complete checkmark */}
          {!isActive && (
            <div className="flex-shrink-0">
              <div className="flex items-center justify-center w-4 h-4 rounded-full bg-emerald-100">
                <svg width="8" height="8" viewBox="0 0 10 10" fill="none">
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
