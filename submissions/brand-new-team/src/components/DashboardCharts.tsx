import React, { useState } from 'react';
import {
  TrendingUp,
  PieChart as PieIcon,
  BarChart3,
  LineChart as LineIcon,
  Table as TableIcon,
  AlertCircle,
  ArrowUpRight,
  ArrowDownRight,
  Layers,
  Target,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  Sliders
} from 'lucide-react';
import { CategoryBudget, SafeZoneConfig, Transaction, ChartType } from '../types';

interface DashboardChartsProps {
  categories: CategoryBudget[];
  safeZone: SafeZoneConfig;
  transactions: Transaction[];
  stealthMode: boolean;
  onOpenBudgetModal: () => void;
}

export const DashboardCharts: React.FC<DashboardChartsProps> = ({
  categories,
  safeZone,
  transactions,
  stealthMode,
  onOpenBudgetModal,
}) => {
  const [selectedChartType, setSelectedChartType] = useState<ChartType>('bar');

  const totalDebit = categories.reduce((sum, c) => sum + c.spent, 0);
  const totalAllocatedBudget = categories.reduce((sum, c) => sum + c.monthlyLimit, 0);

  const formatCurrency = (val: number) => {
    if (stealthMode) return '₹••••';
    return `₹${val.toLocaleString('en-IN')}`;
  };

  // Sort categories by highest spend or allocation
  const sortedCategories = [...categories].sort((a, b) => b.spent - a.spent);

  // Group by Needs vs Wants vs Investments
  const needsSpend = categories.filter((c) => c.isNeed && c.key !== 'Investments').reduce((s, c) => s + c.spent, 0);
  const wantsSpend = categories.filter((c) => !c.isNeed).reduce((s, c) => s + c.spent, 0);
  const investmentsSpend = categories.find((c) => c.key === 'Investments')?.spent || 0;

  const needsPercent = totalDebit > 0 ? Math.round((needsSpend / totalDebit) * 100) : 0;
  const wantsPercent = totalDebit > 0 ? Math.round((wantsSpend / totalDebit) * 100) : 0;
  const investmentsPercent = totalDebit > 0 ? Math.round((investmentsSpend / totalDebit) * 100) : 0;

  // Maximum spend in daily history for scaling
  const maxDaySpend = Math.max(
    ...safeZone.history.map((h) => h.spent),
    safeZone.dailySafeLimit * 1.5,
    2000
  );

  // Metrics for Safe vs Over in history
  const safeDaysCount = safeZone.history.filter((h) => h.spent <= safeZone.dailySafeLimit).length;
  const overDaysCount = safeZone.history.length - safeDaysCount;

  return (
    <div className="space-y-6 mb-8">
      {/* 4 Summary Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Total Expenses */}
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>Total Expenses</span>
            <div className="p-1 rounded bg-rose-500/10 text-rose-400">
              <ArrowDownRight className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-bold font-mono text-white mb-1">
            {formatCurrency(totalDebit)}
          </div>
          <div className="text-[11px] text-slate-400">
            Of {formatCurrency(safeZone.monthlySafeLimit)} monthly safe limit
          </div>
        </div>

        {/* Card 2: User Input Monthly Budget */}
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>Monthly Budget</span>
            <button
              onClick={onOpenBudgetModal}
              className="p-1 rounded bg-indigo-500/10 text-indigo-400 hover:text-indigo-300"
              title="Edit Monthly Budget"
            >
              <Sliders className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="text-xl sm:text-2xl font-bold font-mono text-white mb-1">
            {formatCurrency(safeZone.monthlyBudget)}
          </div>
          <div className="text-[11px] text-emerald-400">
            Target Savings: {formatCurrency(safeZone.savingsLimit)}
          </div>
        </div>

        {/* Card 3: 1-Day Safe Zone */}
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>1-Day Safe Zone</span>
            <div className="p-1 rounded bg-cyan-500/10 text-cyan-400">
              <Target className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-bold font-mono text-white mb-1">
            {formatCurrency(safeZone.dailySafeLimit)}
          </div>
          <div className="text-[11px] text-slate-400">
            Today&apos;s active: <strong className="text-white font-mono">{formatCurrency(safeZone.todaySpent)}</strong>
          </div>
        </div>

        {/* Card 4: REPLACED "Invested and saved" WITH "Monthly safe zone limit" */}
        <div className="p-4 rounded-2xl bg-slate-900 border border-indigo-500/30 shadow-md relative overflow-hidden">
          <div className="flex items-center justify-between text-xs text-indigo-300 mb-2">
            <span className="font-semibold">Monthly Safe Zone Limit</span>
            <div className="p-1 rounded bg-indigo-500/20 text-indigo-400">
              <ShieldCheck className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="text-xl sm:text-2xl font-bold font-mono text-indigo-300 mb-1">
            {formatCurrency(safeZone.monthlySafeLimit)}
          </div>
          <div className="text-[11px] text-slate-400">
            {safeZone.monthSpent > safeZone.monthlySafeLimit ? (
              <span className="text-rose-400 font-semibold">Exceeded safe cap</span>
            ) : (
              <span>Safe buffer: <strong className="text-emerald-400 font-mono">{formatCurrency(safeZone.monthlySafeLimit - safeZone.monthSpent)}</strong></span>
            )}
          </div>
        </div>
      </div>

      {/* Main Row: Daily Velocity Multi-Chart UI + Suggested Category Allocation */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left (2 cols): Daily Spending Velocity vs Safe Zone with Interactive Chart Selector */}
        <div className="lg:col-span-2 p-5 rounded-3xl bg-slate-900 border border-slate-800 shadow-lg flex flex-col justify-between">
          <div>
            {/* Chart Header & Format Selectors */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <span>Daily Spending Velocity vs Safe Zone</span>
                </h3>
                <p className="text-[11px] text-slate-400">
                  Select view: Bar Chart, Line Curve, Pie Breakdown, or Data Table
                </p>
              </div>

              {/* Chart Selector Buttons: Bar, Line, Pie, Table */}
              <div className="flex items-center p-1 bg-slate-950 rounded-xl border border-slate-800 self-start sm:self-auto text-xs">
                <button
                  type="button"
                  onClick={() => setSelectedChartType('bar')}
                  className={`px-2.5 py-1 rounded-lg flex items-center gap-1 transition-all ${
                    selectedChartType === 'bar'
                      ? 'bg-cyan-500 text-slate-950 font-bold shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  title="Bar Chart View"
                >
                  <BarChart3 className="w-3.5 h-3.5" />
                  <span>Bar</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedChartType('line')}
                  className={`px-2.5 py-1 rounded-lg flex items-center gap-1 transition-all ${
                    selectedChartType === 'line'
                      ? 'bg-cyan-500 text-slate-950 font-bold shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  title="Line / Curve View"
                >
                  <LineIcon className="w-3.5 h-3.5" />
                  <span>Line</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedChartType('pie')}
                  className={`px-2.5 py-1 rounded-lg flex items-center gap-1 transition-all ${
                    selectedChartType === 'pie'
                      ? 'bg-cyan-500 text-slate-950 font-bold shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  title="Pie / Donut View"
                >
                  <PieIcon className="w-3.5 h-3.5" />
                  <span>Pie</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedChartType('table')}
                  className={`px-2.5 py-1 rounded-lg flex items-center gap-1 transition-all ${
                    selectedChartType === 'table'
                      ? 'bg-cyan-500 text-slate-950 font-bold shadow'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  title="Data Table View"
                >
                  <TableIcon className="w-3.5 h-3.5" />
                  <span>Table</span>
                </button>
              </div>
            </div>

            {/* DYNAMIC CHART RENDER BASED ON SELECTED TYPE */}
            {selectedChartType === 'bar' && (
              /* FORMAT 1: BAR CHART */
              <div className="relative h-56 w-full pt-4 pb-6 flex items-end justify-between gap-1.5 sm:gap-2">
                {/* Safe Limit Reference Line */}
                <div
                  className="absolute inset-x-0 border-b border-dashed border-cyan-400/80 z-10 pointer-events-none flex items-center justify-end pr-2"
                  style={{
                    bottom: `${Math.min(92, Math.max(12, (safeZone.dailySafeLimit / maxDaySpend) * 100))}%`,
                  }}
                >
                  <span className="text-[10px] font-mono text-cyan-300 bg-slate-950/90 px-1.5 py-0.5 rounded border border-cyan-500/30">
                    Safe Line: ₹{safeZone.dailySafeLimit}
                  </span>
                </div>

                {safeZone.history.map((day, idx) => {
                  const heightPercent = Math.max(6, Math.min(100, Math.round((day.spent / maxDaySpend) * 100)));
                  const isOver = day.spent > safeZone.dailySafeLimit;
                  const isToday = idx === safeZone.history.length - 1;

                  return (
                    <div
                      key={day.date + idx}
                      className="relative flex-1 flex flex-col items-center h-full justify-end group cursor-pointer"
                    >
                      <div className="absolute -top-9 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-30 bg-slate-950 border border-slate-700 text-white text-[10px] font-mono px-2 py-0.5 rounded shadow whitespace-nowrap">
                        {day.date}: ₹{day.spent}
                      </div>

                      <div
                        className={`w-full max-w-[28px] rounded-t-lg transition-all duration-300 ${
                          isToday
                            ? isOver
                              ? 'bg-rose-500 ring-2 ring-rose-400'
                              : 'bg-emerald-400 ring-2 ring-emerald-300'
                            : isOver
                            ? 'bg-rose-500/80 hover:bg-rose-500'
                            : 'bg-emerald-500/70 hover:bg-emerald-400'
                        }`}
                        style={{ height: `${heightPercent}%` }}
                      />

                      <span className={`text-[10px] mt-2 font-mono truncate ${isToday ? 'text-cyan-400 font-bold' : 'text-slate-500'}`}>
                        {day.dayLabel}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {selectedChartType === 'line' && (
              /* FORMAT 2: LINE / AREA CURVE CHART */
              <div className="relative h-56 w-full pt-4 pb-4 flex flex-col justify-end">
                <div
                  className="absolute inset-x-0 border-b border-dashed border-cyan-400/80 z-10 pointer-events-none flex items-center justify-end pr-2"
                  style={{
                    bottom: `${Math.min(90, Math.max(15, (safeZone.dailySafeLimit / maxDaySpend) * 100))}%`,
                  }}
                >
                  <span className="text-[10px] font-mono text-cyan-300 bg-slate-950/90 px-1.5 py-0.5 rounded border border-cyan-500/30">
                    Safe Limit Line: ₹{safeZone.dailySafeLimit}
                  </span>
                </div>

                {/* SVG Curve */}
                <svg className="w-full h-44 overflow-visible" preserveAspectRatio="none" viewBox="0 0 700 200">
                  <defs>
                    <linearGradient id="velocityGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.4" />
                      <stop offset="100%" stopColor="#22d3ee" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  {/* Area fill */}
                  <path
                    d={`M 0,200 ${safeZone.history
                      .map((d, i) => {
                        const x = (i / (safeZone.history.length - 1)) * 700;
                        const y = 200 - Math.min(190, (d.spent / maxDaySpend) * 190);
                        return `L ${x},${y}`;
                      })
                      .join(' ')} L 700,200 Z`}
                    fill="url(#velocityGrad)"
                  />

                  {/* Line stroke */}
                  <path
                    d={`M ${safeZone.history
                      .map((d, i) => {
                        const x = (i / (safeZone.history.length - 1)) * 700;
                        const y = 200 - Math.min(190, (d.spent / maxDaySpend) * 190);
                        return `${i === 0 ? '' : 'L '}${x},${y}`;
                      })
                      .join(' ')}`}
                    fill="none"
                    stroke="#22d3ee"
                    strokeWidth="3"
                  />

                  {/* Data Points */}
                  {safeZone.history.map((d, i) => {
                    const x = (i / (safeZone.history.length - 1)) * 700;
                    const y = 200 - Math.min(190, (d.spent / maxDaySpend) * 190);
                    const isOver = d.spent > safeZone.dailySafeLimit;
                    return (
                      <circle
                        key={i}
                        cx={x}
                        cy={y}
                        r="5"
                        fill={isOver ? '#ef4444' : '#10b981'}
                        stroke="#0f172a"
                        strokeWidth="2"
                      />
                    );
                  })}
                </svg>

                {/* X-axis labels */}
                <div className="flex justify-between pt-2 text-[10px] font-mono text-slate-400">
                  {safeZone.history.map((d, i) => (
                    <span key={i}>{d.dayLabel}</span>
                  ))}
                </div>
              </div>
            )}

            {selectedChartType === 'pie' && (
              /* FORMAT 3: PIE / DONUT BREAKDOWN */
              <div className="h-56 w-full flex flex-col sm:flex-row items-center justify-around gap-4 pt-2">
                {/* Visual SVG Donut */}
                <div className="relative w-36 h-36 flex items-center justify-center">
                  <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                    <circle
                      cx="50"
                      cy="50"
                      r="40"
                      fill="transparent"
                      stroke="#ef4444"
                      strokeWidth="14"
                      strokeDasharray={`${(overDaysCount / safeZone.history.length) * 251.2} 251.2`}
                      strokeDashoffset="0"
                    />
                    <circle
                      cx="50"
                      cy="50"
                      r="40"
                      fill="transparent"
                      stroke="#10b981"
                      strokeWidth="14"
                      strokeDasharray={`${(safeDaysCount / safeZone.history.length) * 251.2} 251.2`}
                      strokeDashoffset={`-${(overDaysCount / safeZone.history.length) * 251.2}`}
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                    <span className="text-xl font-bold font-mono text-white">
                      {Math.round((safeDaysCount / safeZone.history.length) * 100)}%
                    </span>
                    <span className="text-[9px] uppercase font-bold text-emerald-400">
                      Safe Rate
                    </span>
                  </div>
                </div>

                {/* Legend & Stats */}
                <div className="space-y-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-emerald-500" />
                    <span className="text-slate-300">
                      In Safe Zone: <strong className="text-white font-mono">{safeDaysCount} Days</strong>
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded-full bg-rose-500" />
                    <span className="text-slate-300">
                      Over Daily Limit: <strong className="text-rose-400 font-mono">{overDaysCount} Days</strong>
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 pt-1">
                    Daily Limit: ₹{safeZone.dailySafeLimit.toLocaleString('en-IN')}/day
                  </p>
                </div>
              </div>
            )}

            {selectedChartType === 'table' && (
              /* FORMAT 4: DATA TABLE BREAKDOWN */
              <div className="h-56 overflow-y-auto border border-slate-800 rounded-xl bg-slate-950/60 text-xs">
                <table className="w-full text-left">
                  <thead className="bg-slate-900 sticky top-0 text-slate-400 border-b border-slate-800">
                    <tr>
                      <th className="py-2 px-3">Date</th>
                      <th className="py-2 px-3">Spent</th>
                      <th className="py-2 px-3">Safe Limit</th>
                      <th className="py-2 px-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {safeZone.history.map((d, i) => {
                      const isOver = d.spent > safeZone.dailySafeLimit;
                      return (
                        <tr key={i} className="hover:bg-slate-900/40">
                          <td className="py-1.5 px-3">{d.date} ({d.dayLabel})</td>
                          <td className={`py-1.5 px-3 font-bold ${isOver ? 'text-rose-400' : 'text-slate-200'}`}>
                            ₹{d.spent.toLocaleString('en-IN')}
                          </td>
                          <td className="py-1.5 px-3 text-slate-400">
                            ₹{safeZone.dailySafeLimit.toLocaleString('en-IN')}
                          </td>
                          <td className="py-1.5 px-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${isOver ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'}`}>
                              {isOver ? 'Exceeded' : 'Safe Zone'}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* 50 / 30 / 20 Financial Rule Gauge */}
          <div className="pt-4 mt-3 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-1.5 text-slate-300 font-medium">
              <Layers className="w-4 h-4 text-indigo-400" />
              <span>50/30/20 Rule:</span>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span className="text-sky-400">Needs: <strong>{needsPercent}%</strong></span>
              <span className="text-violet-400">Wants: <strong>{wantsPercent}%</strong></span>
              <span className="text-emerald-400">Savings Target: <strong>{safeZone.monthlyBudget > 0 ? Math.round((safeZone.savingsLimit / safeZone.monthlyBudget) * 100) : 0}%</strong></span>
            </div>
          </div>
        </div>

        {/* Right (1 col): DISPLAY THE SUGGESTED EXISTING CATEGORY THE AI/USER INPUTTED INTO THE CATEGORY ALLOCATION */}
        <div className="p-5 rounded-3xl bg-slate-900 border border-slate-800 shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                  <PieIcon className="w-4 h-4 text-indigo-400" />
                  <span>Category Allocation</span>
                </h3>
                <p className="text-[11px] text-slate-400">
                  AI-suggested &amp; user-inputted category budgets
                </p>
              </div>

              <button
                onClick={onOpenBudgetModal}
                className="text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold"
              >
                Edit Allocations
              </button>
            </div>

            {/* Safe Cap Exceeded or Matched status */}
            {totalAllocatedBudget > safeZone.monthlySafeLimit && safeZone.monthlySafeLimit > 0 ? (
              <div className="mb-3 p-2 rounded-xl bg-rose-500/15 border border-rose-500/40 text-rose-300 text-[11px] flex items-center justify-between gap-1.5">
                <span className="font-semibold flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                  <span>Safe Cap Limit Exceeded!</span>
                </span>
                <span className="font-mono font-bold text-rose-300">
                  +{formatCurrency(totalAllocatedBudget - safeZone.monthlySafeLimit)}
                </span>
              </div>
            ) : totalAllocatedBudget === safeZone.monthlySafeLimit && safeZone.monthlySafeLimit > 0 ? (
              <div className="mb-3 p-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-[10px] flex items-center justify-between">
                <span className="flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Sum equals Monthly Safe Cap</span>
                </span>
                <span className="font-mono font-bold text-emerald-400">100%</span>
              </div>
            ) : null}

            {/* List of existing categories with AI / User Inputted Limits */}
            <div className="space-y-3 mt-3">
              {sortedCategories.slice(0, 8).map((cat) => {
                const percentOfBudget = cat.monthlyLimit > 0
                  ? Math.min(100, Math.round((cat.spent / cat.monthlyLimit) * 100))
                  : 0;
                const isOver = cat.spent > cat.monthlyLimit;

                return (
                  <div key={cat.key} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-1.5">
                        <span
                          className="w-2.5 h-2.5 rounded-sm"
                          style={{ backgroundColor: cat.color }}
                        />
                        <span className="text-slate-200 font-medium">{cat.name}</span>
                        {/* Tag: AI Suggested or User Custom */}
                        {cat.isUserCustomized ? (
                          <span className="text-[9px] px-1 py-0.2 rounded bg-slate-800 text-slate-400 font-mono">
                            Custom
                          </span>
                        ) : (
                          <span className="text-[9px] px-1 py-0.2 rounded bg-indigo-500/10 text-indigo-400 font-mono flex items-center gap-0.5">
                            <Sparkles className="w-2.5 h-2.5" />
                            AI
                          </span>
                        )}
                      </div>

                      {/* Display spend vs AI/user inputted allocation */}
                      <div className="flex items-center gap-1.5 font-mono text-xs">
                        <span className={isOver ? 'text-rose-400 font-bold' : 'text-slate-200'}>
                          {formatCurrency(cat.spent)}
                        </span>
                        <span className="text-slate-500">/</span>
                        <span className="text-slate-400">
                          {formatCurrency(cat.monthlyLimit)}
                        </span>
                      </div>
                    </div>

                    {/* Visual burn bar */}
                    <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-300"
                        style={{
                          width: `${percentOfBudget}%`,
                          backgroundColor: isOver ? '#ef4444' : cat.color,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="pt-3 mt-4 border-t border-slate-800 flex flex-wrap items-center justify-between text-xs text-slate-400 gap-2">
            <div>
              <span>Total Amount: </span>
              <strong className={`font-mono ${totalAllocatedBudget > safeZone.monthlySafeLimit ? 'text-rose-400' : 'text-white'}`}>
                {formatCurrency(totalAllocatedBudget)}
              </strong>
              <span className="text-slate-500"> / </span>
              <span className="text-cyan-300 font-mono">{formatCurrency(safeZone.monthlySafeLimit)}</span>
            </div>
            <button
              onClick={onOpenBudgetModal}
              className="text-cyan-400 hover:underline text-[11px] font-semibold"
            >
              Adjust Category Splits &rarr;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
