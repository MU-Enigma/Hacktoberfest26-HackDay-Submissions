import React from 'react';

interface WispendLogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
  showTagline?: boolean;
}

export const WispendLogo: React.FC<WispendLogoProps> = ({
  className = '',
  size = 'md',
  showText = true,
  showTagline = true,
}) => {
  const iconDimensions = {
    sm: 'w-7 h-7',
    md: 'w-9 h-9',
    lg: 'w-11 h-11',
  }[size];

  const titleSizes = {
    sm: 'text-sm',
    md: 'text-base sm:text-lg',
    lg: 'text-xl sm:text-2xl',
  }[size];

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Wispend Stylized Monogram / Emblem */}
      <div
        className={`${iconDimensions} relative rounded-xl p-[2px] bg-gradient-to-tr from-cyan-500 via-indigo-500 to-emerald-400 shadow-lg shadow-cyan-500/25 flex-shrink-0 group`}
      >
        <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center overflow-hidden relative">
          {/* Background ambient glow */}
          <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/20 via-cyan-500/10 to-transparent pointer-events-none" />

          {/* Precision SVG 'W' Monogram for Wispend */}
          <svg
            viewBox="0 0 32 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="w-5 h-5 relative z-10 transition-transform duration-300 group-hover:scale-105"
          >
            <defs>
              <linearGradient id="wispendGradPrimary" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#06b6d4" />
                <stop offset="50%" stopColor="#6366f1" />
                <stop offset="100%" stopColor="#10b981" />
              </linearGradient>
              <linearGradient id="wispendGradSecondary" x1="100%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor="#38bdf8" />
                <stop offset="100%" stopColor="#818cf8" />
              </linearGradient>
            </defs>

            {/* Left Wing of W */}
            <path
              d="M5 8 L10.5 24 C10.8 24.8 11.8 25.2 12.6 24.8 L16 22 L11 9 C10.8 8.4 10.1 8 9.5 8 Z"
              fill="url(#wispendGradPrimary)"
            />

            {/* Center Peak of W */}
            <path
              d="M16 22 L19.4 24.8 C20.2 25.2 21.2 24.8 21.5 24 L27 8 L22.5 8 C21.9 8 21.2 8.4 21 9 L16 22 Z"
              fill="url(#wispendGradPrimary)"
            />

            {/* Inner Financial Chevron / Safe Arch */}
            <path
              d="M12 11 L16 19 L20 11"
              stroke="url(#wispendGradSecondary)"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Smart Spending Dot */}
            <circle cx="16" cy="7.5" r="1.5" fill="#34d399" />
          </svg>
        </div>
      </div>

      {/* Brand Name Typography */}
      {showText && (
        <div>
          <div className="flex items-center gap-2">
            <span className={`${titleSizes} font-extrabold tracking-tight text-white flex items-center`}>
              <span>Wis</span>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-indigo-300 to-emerald-400">
                pend
              </span>
            </span>
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 hidden sm:inline-block">
              Safe Zone
            </span>
          </div>
          {showTagline && (
            <p className="text-[11px] text-slate-400 hidden sm:block">
              PhonePe Statement Analytics &amp; Smart Spending
            </p>
          )}
        </div>
      )}
    </div>
  );
};
