import React from 'react';
import {
  Shield,
  ShieldCheck,
  ShieldAlert,
  Calendar,
  Sparkles,
  TrendingUp,
  Sliders,
  DollarSign,
  PiggyBank,
  CheckCircle2,
  AlertTriangle,
  ArrowRight
} from 'lucide-react';
import { SafeZoneConfig } from '../types';

interface SafeZoneBannerProps {
  safeZone: SafeZoneConfig;
  stealthMode: boolean;
  onSimulateSpend: (amount: number, description: string) => void;
  onOpenBudgetModal: () => void;
  onOpenSafeZoneModal: () => void;
}

export const SafeZoneBanner: React.FC<SafeZoneBannerProps> = ({
  safeZone,
  stealthMode,
  onSimulateSpend,
  onOpenBudgetModal,
  onOpenSafeZoneModal,
}) => {
  const {
    dailySafeLimit,
    todaySpent,
    monthlyBudget,
    savingsLimit,
    monthlySafeLimit,
    monthSpent,
  } = safeZone;

  // 1-Day Safe Zone metrics
  const remainingDaily = Math.max(0, dailySafeLimit - todaySpent);
  const dailyPercentUsed = dailySafeLimit > 0 ? Math.min(100, Math.round((todaySpent / dailySafeLimit) * 100)) : 0;
  const isDailyOver = dailySafeLimit > 0 && todaySpent > dailySafeLimit;
  const isDailyNear = dailySafeLimit > 0 && todaySpent >= dailySafeLimit * 0.8 && !isDailyOver;

  // Monthly Safe Zone metrics
  const remainingMonthly = Math.max(0, monthlySafeLimit - monthSpent);
  const monthlyPercentUsed = monthlySafeLimit > 0 ? Math.min(100, Math.round((monthSpent / monthlySafeLimit) * 100)) : 0;
  const isMonthlyOver = monthlySafeLimit > 0 && monthSpent > monthlySafeLimit;
  const isMonthlyNear = monthlySafeLimit > 0 && monthSpent >= monthlySafeLimit * 0.85 && !isMonthlyOver;

  const formatCurrency = (val: number) => {
    if (stealthMode) return '₹••••';
    return `₹${val.toLocaleString('en-IN')}`;
  };

  return (
    <div className="space-y-4 mb-8">
      {/* 2-Column Responsive Grid: 1-Day Safe Zone UI + Monthly Safe Zone UI */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* 1. 1-DAY SAFE ZONE UI */}
        <div className="relative overflow-hidden rounded-3xl border border-slate-800 bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 p-5 sm:p-6 shadow-xl text-slate-100 flex flex-col justify-between">
          {/* Subtle Ambient Glow */}
          <div className="absolute -top-12 -right-12 w-48 h-48 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

          <div>
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className={`p-2.5 rounded-2xl border ${
                  isDailyOver
                    ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                    : isDailyNear
                    ? 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                    : 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400'
                }`}>
                  {isDailyOver ? <ShieldAlert className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-extrabold text-white tracking-tight">
                      1-Day Safe Spending Zone
                    </h3>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                      dailySafeLimit === 0
                        ? 'bg-slate-800 text-slate-400 border-slate-700'
                        : isDailyOver
                        ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                        : isDailyNear
                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                    }`}>
                      {dailySafeLimit === 0 ? 'Awaiting Statement' : isDailyOver ? 'Limit Exceeded' : isDailyNear ? 'Caution (80%+)' : 'Safe Zone Active'}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Your calculated safe limit for discretionary daily spending
                  </p>
                </div>
              </div>

              {/* Action: De-select items from Safe Zone */}
              <button
                onClick={onOpenSafeZoneModal}
                className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 transition-colors underline whitespace-nowrap"
                title="De-select specific expenses so they don't penalize your 1-day safe zone"
              >
                De-select Expenses
              </button>
            </div>

            {/* Figures Display */}
            <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800/80 mb-4">
              <div className="flex items-baseline justify-between mb-2">
                <div>
                  <span className="text-xs text-slate-400 block font-medium mb-0.5">Today&apos;s Active Spend</span>
                  <span className="text-2xl sm:text-3xl font-bold font-mono text-white">
                    {formatCurrency(todaySpent)}
                  </span>
                  <span className="text-xs text-slate-500 font-mono ml-1.5">
                    / {formatCurrency(dailySafeLimit)} daily limit
                  </span>
                </div>

                <div className="text-right">
                  <span className="text-xs text-slate-400 block font-medium mb-0.5">Safe Daily Margin</span>
                  {isDailyOver ? (
                    <span className="text-sm font-bold font-mono text-rose-400 flex items-center gap-1 justify-end">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      +{formatCurrency(todaySpent - dailySafeLimit)} Over
                    </span>
                  ) : (
                    <span className="text-sm font-bold font-mono text-emerald-400 flex items-center gap-1 justify-end">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {formatCurrency(remainingDaily)} buffer left
                    </span>
                  )}
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full h-3 rounded-full bg-slate-800 overflow-hidden relative">
                <div
                  className={`h-full transition-all duration-500 rounded-full ${
                    isDailyOver
                      ? 'bg-rose-500'
                      : isDailyNear
                      ? 'bg-amber-500'
                      : 'bg-gradient-to-r from-emerald-500 to-cyan-400'
                  }`}
                  style={{ width: `${dailyPercentUsed}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2 font-mono">
                <span>{dailyPercentUsed}% consumed today</span>
                <span>Reset at midnight</span>
              </div>
            </div>
          </div>

          {/* Quick simulator row */}
          <div className="pt-2 flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/80">
            <span className="text-[11px]">Quick Spend Simulator:</span>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => onSimulateSpend(150, 'Chai & Coffee')}
                className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] transition-colors"
              >
                +₹150 Chai
              </button>
              <button
                onClick={() => onSimulateSpend(450, 'Zomato Food Order')}
                className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] transition-colors"
              >
                +₹450 Food
              </button>
              <button
                onClick={() => onSimulateSpend(1500, 'Shopping Impulse')}
                className="px-2 py-1 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/20 text-[11px] transition-colors"
                title="Test exceeding 1-day safe limit"
              >
                +₹1,500 Breach
              </button>
            </div>
          </div>
        </div>

        {/* 2. MONTHLY SAFE ZONE UI */}
        <div className="relative overflow-hidden rounded-3xl border border-slate-800 bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 p-5 sm:p-6 shadow-xl text-slate-100 flex flex-col justify-between">
          {/* Subtle Ambient Glow */}
          <div className="absolute -top-12 -right-12 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

          <div>
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                  <PiggyBank className="w-5 h-5" />
                </div>

                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-extrabold text-white tracking-tight">
                      Monthly Safe Zone UI
                    </h3>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      Cap: {formatCurrency(monthlySafeLimit)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Budget ({formatCurrency(monthlyBudget)}) minus AI Savings Target ({formatCurrency(savingsLimit)})
                  </p>
                </div>
              </div>

              {/* Adjust Monthly Budget & Savings */}
              <button
                onClick={onOpenBudgetModal}
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors flex items-center gap-1"
                title="Customize Monthly Budget & AI Savings Limit"
              >
                <Sliders className="w-3.5 h-3.5" />
                <span>Edit Targets</span>
              </button>
            </div>

            {/* Figures Display */}
            <div className="p-4 rounded-2xl bg-slate-950/70 border border-slate-800/80 mb-4">
              <div className="flex items-baseline justify-between mb-2">
                <div>
                  <span className="text-xs text-slate-400 block font-medium mb-0.5">Month-to-Date Spend</span>
                  <span className="text-2xl sm:text-3xl font-bold font-mono text-white">
                    {formatCurrency(monthSpent)}
                  </span>
                  <span className="text-xs text-slate-500 font-mono ml-1.5">
                    / {formatCurrency(monthlySafeLimit)} safe cap
                  </span>
                </div>

                <div className="text-right">
                  <span className="text-xs text-slate-400 block font-medium mb-0.5">Remaining Safe Buffer</span>
                  {isMonthlyOver ? (
                    <span className="text-sm font-bold font-mono text-rose-400">
                      -{formatCurrency(monthSpent - monthlySafeLimit)} Over Cap
                    </span>
                  ) : (
                    <span className="text-sm font-bold font-mono text-emerald-400">
                      {formatCurrency(remainingMonthly)} buffer left
                    </span>
                  )}
                </div>
              </div>

              {/* Progress bar */}
              <div className="w-full h-3 rounded-full bg-slate-800 overflow-hidden relative">
                <div
                  className={`h-full transition-all duration-500 rounded-full ${
                    isMonthlyOver
                      ? 'bg-rose-500'
                      : isMonthlyNear
                      ? 'bg-amber-500'
                      : 'bg-gradient-to-r from-indigo-500 to-emerald-400'
                  }`}
                  style={{ width: `${monthlyPercentUsed}%` }}
                />
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2 font-mono">
                <span>{monthlyPercentUsed}% of monthly safe limit spent</span>
                <span>Savings Target: {formatCurrency(savingsLimit)}</span>
              </div>
            </div>
          </div>

          {/* Breakdown summary row */}
          <div className="pt-2 flex items-center justify-between text-xs text-slate-400 border-t border-slate-800/80">
            <div className="flex items-center gap-3">
              <span>Budget: <strong className="text-white font-mono">{formatCurrency(monthlyBudget)}</strong></span>
              <span>·</span>
              <span className="text-emerald-400">Protected Savings: <strong className="font-mono">{formatCurrency(savingsLimit)}</strong></span>
            </div>
            <button
              onClick={onOpenBudgetModal}
              className="text-[11px] text-slate-300 hover:text-white flex items-center gap-1 font-semibold"
            >
              <span>Category Splits</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
