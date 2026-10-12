import React, { useState, useEffect } from 'react';
import {
  X,
  Sparkles,
  Check,
  Sliders,
  AlertTriangle,
  ShieldCheck,
  PiggyBank,
  DollarSign,
  Layers,
  ArrowRight,
  CheckCircle2,
} from 'lucide-react';
import { CategoryBudget, CategoryKey } from '../types';
import { calculateAiCategoryDivision, evaluateSafeCapStatus } from '../utils/budgetCalculations';

interface BudgetManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  categories: CategoryBudget[];
  monthlyBudget: number;
  savingsLimit: number;
  aiSuggestedSavingsLimit: number;
  currentDailySafeLimit: number;
  onSaveBudgets: (
    updatedBudgets: CategoryBudget[],
    updatedMonthlyBudget: number,
    updatedSavingsLimit: number,
    updatedDailySafeLimit: number
  ) => void;
}

export const BudgetManagerModal: React.FC<BudgetManagerModalProps> = ({
  isOpen,
  onClose,
  categories,
  monthlyBudget,
  savingsLimit,
  aiSuggestedSavingsLimit,
  currentDailySafeLimit,
  onSaveBudgets,
}) => {
  // 1. User Input for Monthly Budget (Defaults to 3,000 if unset)
  const [budgetInput, setBudgetInput] = useState<number>(monthlyBudget > 0 ? monthlyBudget : 3000);

  // 2. AI Suggestion for Saving Limit (User editable)
  const [savingsInput, setSavingsInput] = useState<number>(savingsLimit);

  // 3. Category limits (Divided by AI, user editable)
  const [localBudgets, setLocalBudgets] = useState<CategoryBudget[]>(categories);

  // 4. Daily Safe Limit (Defaults to 100 rupees)
  const [dailySafeInput, setDailySafeInput] = useState<number>(currentDailySafeLimit > 0 ? currentDailySafeLimit : 100);

  useEffect(() => {
    if (isOpen) {
      setBudgetInput(monthlyBudget > 0 ? monthlyBudget : 3000);
      setSavingsInput(savingsLimit);
      setLocalBudgets(categories);
      setDailySafeInput(currentDailySafeLimit > 0 ? currentDailySafeLimit : 100);
    }
  }, [isOpen, monthlyBudget, savingsLimit, categories, currentDailySafeLimit]);

  if (!isOpen) return null;

  // Monthly safe spending cap = Monthly Budget - Savings Limit
  const disposableMonthlyCap = Math.max(0, budgetInput - savingsInput);

  // Re-distribute budget across categories using AI division
  // GUARANTEED: sum of AI category division strictly equals disposableMonthlyCap
  const handleAutoDivideWithAi = () => {
    const newAllocations = calculateAiCategoryDivision(disposableMonthlyCap);

    const newBudgets = localBudgets.map((cat) => {
      const computedLimit = newAllocations[cat.key] ?? 0;
      return {
        ...cat,
        monthlyLimit: computedLimit,
        aiSuggestedLimit: computedLimit,
        isUserCustomized: false,
      };
    });

    setLocalBudgets(newBudgets);
    const newDaily = disposableMonthlyCap === 3000 ? 100 : Math.max(0, Math.round(disposableMonthlyCap / 30 / 10) * 10);
    setDailySafeInput(newDaily);
  };

  const handleApplyAiSavingsSuggestion = () => {
    // AI suggests 25% savings limit from monthly budget
    const suggested = Math.round((budgetInput * 0.25) / 1000) * 1000;
    setSavingsInput(suggested);
  };

  const handleCategoryLimitChange = (key: CategoryKey, val: number) => {
    setLocalBudgets((prev) =>
      prev.map((cat) =>
        cat.key === key
          ? { ...cat, monthlyLimit: Math.max(0, val), isUserCustomized: true }
          : cat
      )
    );
  };

  const totalAllocatedToCategories = localBudgets.reduce((acc, cat) => acc + cat.monthlyLimit, 0);
  const totalAllocatedOverall = totalAllocatedToCategories + savingsInput;
  const difference = budgetInput - totalAllocatedOverall;
  const safeCapStatus = evaluateSafeCapStatus(localBudgets, disposableMonthlyCap);

  const handleSave = () => {
    onSaveBudgets(localBudgets, budgetInput, savingsInput, dailySafeInput);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl max-h-[92vh] flex flex-col bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl text-slate-100 overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-start justify-between bg-slate-900/90 backdrop-blur">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                <Sliders className="w-5 h-5" />
              </span>
              <h3 className="text-xl font-bold text-white">Monthly Budget &amp; AI Allocation</h3>
            </div>
            <p className="text-xs text-slate-400">
              Input your monthly budget &rarr; AI suggests savings limit &rarr; Divide remaining into categories (all user editable).
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Top Controls: 1. Monthly Budget Input + 2. AI Savings Limit Input */}
        <div className="p-6 bg-slate-950 border-b border-slate-800 grid grid-cols-1 sm:grid-cols-3 gap-4">
          {/* Feature 1: User input for monthly budget */}
          <div className="p-3.5 rounded-2xl bg-slate-900 border border-slate-800">
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
              1. Your Monthly Budget (INR ₹)
            </label>
            <div className="flex items-center gap-1.5 bg-slate-950 border border-slate-700 rounded-xl px-3 py-1.5 focus-within:border-indigo-500">
              <span className="text-slate-400 font-mono text-sm">₹</span>
              <input
                type="number"
                step="1000"
                min="5000"
                value={budgetInput}
                onChange={(e) => setBudgetInput(Math.max(0, Number(e.target.value) || 0))}
                className="w-full bg-transparent font-mono font-bold text-white text-base focus:outline-none"
              />
            </div>
            <span className="text-[10px] text-slate-500 mt-1 block">
              Total monthly income / spend pool
            </span>
          </div>

          {/* Feature 2: AI Suggestion for Saving Limit (User editable) */}
          <div className="p-3.5 rounded-2xl bg-slate-900 border border-emerald-500/30">
            <div className="flex items-center justify-between mb-1">
              <label className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
                2. Target Savings Limit
              </label>
              <button
                type="button"
                onClick={handleApplyAiSavingsSuggestion}
                className="text-[10px] text-emerald-300 hover:underline flex items-center gap-0.5"
                title="Apply AI 25% suggestion"
              >
                <Sparkles className="w-2.5 h-2.5" />
                <span>AI 25%</span>
              </button>
            </div>
            <div className="flex items-center gap-1.5 bg-slate-950 border border-emerald-500/40 rounded-xl px-3 py-1.5 focus-within:border-emerald-400">
              <span className="text-emerald-400 font-mono text-sm">₹</span>
              <input
                type="number"
                step="500"
                min="0"
                max={budgetInput}
                value={savingsInput}
                onChange={(e) => setSavingsInput(Math.max(0, Number(e.target.value) || 0))}
                className="w-full bg-transparent font-mono font-bold text-emerald-400 text-base focus:outline-none"
              />
            </div>
            <span className="text-[10px] text-slate-400 mt-1 block">
              {budgetInput > 0 ? `${Math.round((savingsInput / budgetInput) * 100)}% of monthly budget` : 'Savings goal'}
            </span>
          </div>

          {/* Feature 3: Safe Monthly Disposable Spending Cap & 1-Day Safe Zone (Editable) */}
          <div className="p-3.5 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col justify-between">
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-cyan-400 block mb-1">
                3. Monthly Safe Cap
              </span>
              <div className="text-xl font-bold font-mono text-cyan-300">
                ₹{disposableMonthlyCap.toLocaleString('en-IN')}
              </div>
              <span className="text-[10px] text-slate-500 mt-0.5 block">
                Budget - Savings target
              </span>
            </div>

            <div className="pt-2 border-t border-slate-800">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] uppercase font-bold text-indigo-400">
                  4. 1-Day Safe Zone
                </span>
                <span className="text-[9px] text-slate-400">(Editable)</span>
              </div>
              <div className="flex items-center gap-1 bg-slate-950 border border-indigo-500/40 rounded-lg px-2 py-1">
                <span className="text-indigo-400 font-mono text-xs">₹</span>
                <input
                  type="number"
                  step="100"
                  min="0"
                  value={dailySafeInput}
                  onChange={(e) => setDailySafeInput(Math.max(0, Number(e.target.value) || 0))}
                  className="w-full bg-transparent font-mono font-bold text-white text-xs focus:outline-none"
                />
                <span className="text-slate-500 text-[10px]">/day</span>
              </div>
            </div>
          </div>
        </div>

        {/* Feature 4: Divide monthly safe spending cap into existing categories */}
        <div className="px-6 py-3.5 bg-slate-950/80 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-slate-400">
              Monthly Safe Cap: <strong className="text-cyan-300 font-mono">₹{disposableMonthlyCap.toLocaleString('en-IN')}</strong>
            </span>
            <span>·</span>
            <span className={safeCapStatus.isCapExceeded ? 'text-rose-400 font-bold' : 'text-slate-300'}>
              Total Amount Allocated: <strong className="font-mono">₹{safeCapStatus.totalAllocated.toLocaleString('en-IN')}</strong>
            </span>
            <span>·</span>
            <span className="font-mono text-[11px]">
              {safeCapStatus.isCapExceeded ? (
                <span className="text-rose-400 font-semibold">+₹{safeCapStatus.difference.toLocaleString('en-IN')} Exceeded</span>
              ) : safeCapStatus.isExactMatch ? (
                <span className="text-emerald-400 font-semibold">✓ Exact Match</span>
              ) : (
                <span className="text-amber-400 font-semibold">₹{(disposableMonthlyCap - safeCapStatus.totalAllocated).toLocaleString('en-IN')} Remaining</span>
              )}
            </span>
          </div>

          <button
            onClick={handleAutoDivideWithAi}
            className="px-3.5 py-1.5 rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 font-semibold text-xs flex items-center gap-1.5 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>AI Divide Safe Cap into Categories</span>
          </button>
        </div>

        {/* Safe Cap Limit Exceeded Banner */}
        {safeCapStatus.isCapExceeded && (
          <div className="mx-6 mt-3 p-3 rounded-2xl bg-rose-500/15 border border-rose-500/40 text-rose-300 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              <div>
                <span className="font-bold text-rose-200">Safe Cap Limit Exceeded!</span>
                <span className="text-[11px] text-rose-300 block">
                  {safeCapStatus.anyIndividualExceeds
                    ? `An individual category (₹${safeCapStatus.maxIndividual.toLocaleString('en-IN')}) or category allocation sum (₹${safeCapStatus.totalAllocated.toLocaleString('en-IN')}) is greater than your monthly safe spending cap (₹${disposableMonthlyCap.toLocaleString('en-IN')}) by ₹${safeCapStatus.difference.toLocaleString('en-IN')}.`
                    : `The sum of individual category allocations (₹${safeCapStatus.totalAllocated.toLocaleString('en-IN')}) is greater than your monthly safe spending cap (₹${disposableMonthlyCap.toLocaleString('en-IN')}) by ₹${safeCapStatus.difference.toLocaleString('en-IN')}.`}
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={handleAutoDivideWithAi}
              className="px-3 py-1 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 font-semibold text-xs whitespace-nowrap self-start sm:self-auto"
            >
              Re-balance to Safe Cap
            </button>
          </div>
        )}

        {safeCapStatus.isExactMatch && (
          <div className="mx-6 mt-3 p-2.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span>
                <strong>AI Allocation Balanced:</strong> Sum of category division allocations (₹{safeCapStatus.totalAllocated.toLocaleString('en-IN')}) equals Monthly Safe Cap (₹{disposableMonthlyCap.toLocaleString('en-IN')}).
              </span>
            </div>
            <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              EXACT MATCH
            </span>
          </div>
        )}

        {/* Categories List (User can edit each category) */}
        <div className="p-6 overflow-y-auto space-y-3.5 flex-1">
          {localBudgets.map((cat) => {
            const spentPercent = cat.monthlyLimit > 0
              ? Math.min(100, Math.round((cat.spent / cat.monthlyLimit) * 100))
              : 0;

            return (
              <div
                key={cat.key}
                className="p-3.5 rounded-2xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs flex-shrink-0"
                    style={{ backgroundColor: `${cat.color}20`, color: cat.color }}
                  >
                    {cat.key.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white text-sm">{cat.name}</span>
                      {cat.isUserCustomized ? (
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 font-mono">
                          User Edited
                        </span>
                      ) : (
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono flex items-center gap-0.5">
                          <Sparkles className="w-2.5 h-2.5" />
                          AI Suggested
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5 flex items-center gap-2">
                      <span>Spent so far: <strong className="font-mono text-slate-200">₹{cat.spent.toLocaleString('en-IN')}</strong></span>
                      <span>({spentPercent}%)</span>
                    </div>
                  </div>
                </div>

                {/* Editable limit input */}
                <div className="flex items-center gap-2 self-end sm:self-auto">
                  <span className="text-xs text-slate-400">Limit:</span>
                  <div className="flex items-center bg-slate-900 border border-slate-700 rounded-xl px-2.5 py-1">
                    <span className="text-slate-400 text-xs font-mono mr-1">₹</span>
                    <input
                      type="number"
                      step="500"
                      min="0"
                      value={cat.monthlyLimit}
                      onChange={(e) => handleCategoryLimitChange(cat.key, Number(e.target.value) || 0)}
                      className="w-24 bg-transparent text-sm font-mono font-bold text-white focus:outline-none text-right"
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer Actions */}
        <div className="p-5 border-t border-slate-800 bg-slate-900/90 flex flex-wrap items-center justify-between gap-3">
          <div className="text-xs text-slate-400">
            {difference < 0 ? (
              <span className="text-rose-400 flex items-center gap-1 font-semibold">
                <AlertTriangle className="w-4 h-4" />
                Allocations exceed Monthly Budget by ₹{Math.abs(difference).toLocaleString('en-IN')}
              </span>
            ) : (
              <span className="text-emerald-400 flex items-center gap-1 font-medium">
                <ShieldCheck className="w-4 h-4" />
                Budget Balanced · Target Savings ₹{savingsInput.toLocaleString('en-IN')} Protected
              </span>
            )}
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-emerald-600/20 active:scale-95 transition-all"
            >
              <Check className="w-4 h-4" />
              <span>Apply &amp; Save Targets</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
