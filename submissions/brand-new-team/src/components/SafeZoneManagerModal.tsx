import React from 'react';
import { X, Shield, ShieldAlert, CheckCircle2, AlertCircle, Sparkles, Filter } from 'lucide-react';
import { Transaction, CategoryBudget, CategoryKey } from '../types';

interface SafeZoneManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  transactions: Transaction[];
  categories: CategoryBudget[];
  dailyLimit: number;
  excludedTxIds: Set<string>;
  excludedCategories: Set<CategoryKey>;
  onToggleTxInclusion: (txId: string) => void;
  onToggleCategoryInclusion: (catKey: CategoryKey) => void;
  todayDateStr: string;
}

export const SafeZoneManagerModal: React.FC<SafeZoneManagerModalProps> = ({
  isOpen,
  onClose,
  transactions,
  categories,
  dailyLimit,
  excludedTxIds,
  excludedCategories,
  onToggleTxInclusion,
  onToggleCategoryInclusion,
  todayDateStr,
}) => {
  if (!isOpen) return null;

  // Transactions from today
  const todayDebits = transactions.filter(
    (t) => t.type === 'DEBIT' && t.date === todayDateStr
  );

  // Compute included vs excluded amounts today
  let todayIncludedSum = 0;
  let todayExcludedSum = 0;

  todayDebits.forEach((t) => {
    const isExcluded = excludedTxIds.has(t.id) || excludedCategories.has(t.category);
    if (isExcluded) {
      todayExcludedSum += t.amount;
    } else {
      todayIncludedSum += t.amount;
    }
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl max-h-[90vh] flex flex-col bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl text-slate-100 overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-start justify-between bg-slate-900/90 backdrop-blur">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">
                1-Day Safe Zone Inclusions
              </h3>
              <p className="text-xs text-slate-400">
                De-select non-discretionary expenses or categories so they won&apos;t count against your daily safe limit or break your streak.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Live Impact Pill */}
        <div className="px-6 py-3.5 bg-slate-950 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-4">
            <div>
              <span className="text-slate-400">Daily Safe Limit: </span>
              <strong className="text-white font-mono">₹{dailyLimit.toLocaleString('en-IN')}</strong>
            </div>
            <div>
              <span className="text-slate-400">Today&apos;s Active Safe Spend: </span>
              <strong className="text-emerald-400 font-mono">₹{todayIncludedSum.toLocaleString('en-IN')}</strong>
            </div>
            <div>
              <span className="text-slate-400">Shielded (Excluded): </span>
              <strong className="text-cyan-400 font-mono">₹{todayExcludedSum.toLocaleString('en-IN')}</strong>
            </div>
          </div>
          <span className="text-[11px] text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Streak Protected</span>
          </span>
        </div>

        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {/* Section 1: Category-Level Safe Zone Toggles */}
          <div>
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-indigo-400" />
              <span>Category Safe Zone Rules</span>
            </h4>
            <p className="text-[11px] text-slate-400 mb-3">
              Uncheck categories that should NEVER count against your 1-day safe limit (e.g. Fixed rent transfers, SIP investments).
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              {categories.map((cat) => {
                const isExcluded = excludedCategories.has(cat.key);
                return (
                  <button
                    key={cat.key}
                    type="button"
                    onClick={() => onToggleCategoryInclusion(cat.key)}
                    className={`p-2.5 rounded-xl border text-left transition-all flex items-center justify-between gap-2 ${
                      !isExcluded
                        ? 'bg-slate-950/80 border-slate-700 text-white'
                        : 'bg-slate-950/30 border-slate-800/80 text-slate-500 line-through opacity-70'
                    }`}
                  >
                    <div className="min-w-0">
                      <div className="text-xs font-semibold truncate">{cat.name}</div>
                      <div className="text-[10px] text-slate-400">
                        {!isExcluded ? '✓ In Safe Zone' : '✕ Excluded'}
                      </div>
                    </div>
                    <div
                      className={`w-4 h-4 rounded flex items-center justify-center flex-shrink-0 text-[10px] font-bold ${
                        !isExcluded ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800 text-slate-500'
                      }`}
                    >
                      {!isExcluded ? '✓' : ''}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 2: Individual Today's Transactions De-selection */}
          <div>
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-cyan-400" />
              <span>Today&apos;s Expense De-selection ({todayDebits.length} transactions)</span>
            </h4>
            <p className="text-[11px] text-slate-400 mb-3">
              De-select any specific purchase made today so it doesn&apos;t count toward your 1-day limit.
            </p>

            {todayDebits.length === 0 ? (
              <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800 text-center text-xs text-slate-400">
                No expense transactions logged today yet. As you spend, you can toggle them here!
              </div>
            ) : (
              <div className="space-y-2">
                {todayDebits.map((tx) => {
                  const isExcluded = excludedTxIds.has(tx.id) || excludedCategories.has(tx.category);

                  return (
                    <div
                      key={tx.id}
                      onClick={() => onToggleTxInclusion(tx.id)}
                      className={`p-3 rounded-xl border cursor-pointer transition-all flex items-center justify-between gap-3 ${
                        !isExcluded
                          ? 'bg-slate-950/90 border-slate-700 hover:border-emerald-500/40'
                          : 'bg-slate-950/40 border-slate-800/60 opacity-60'
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <input
                          type="checkbox"
                          checked={!isExcluded}
                          onChange={() => {}}
                          className="w-4 h-4 rounded text-emerald-500 accent-emerald-500 cursor-pointer"
                        />
                        <div className="min-w-0">
                          <p className={`text-xs font-semibold ${!isExcluded ? 'text-white' : 'text-slate-400 line-through'}`}>
                            {tx.description}
                          </p>
                          <div className="text-[10px] text-slate-400 flex items-center gap-2 mt-0.5">
                            <span>Category: {tx.category}</span>
                            <span>·</span>
                            <span>{tx.time || 'Today'}</span>
                          </div>
                        </div>
                      </div>

                      <div className="text-right flex-shrink-0">
                        <div className={`text-xs font-mono font-bold ${!isExcluded ? 'text-white' : 'text-slate-400'}`}>
                          ₹{tx.amount.toLocaleString('en-IN')}
                        </div>
                        <span className={`text-[10px] ${!isExcluded ? 'text-emerald-400' : 'text-cyan-400 font-medium'}`}>
                          {!isExcluded ? 'Counts in Limit' : 'De-selected (Safe)'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-5 border-t border-slate-800 bg-slate-900/90 flex items-center justify-between">
          <span className="text-xs text-slate-400">
            Changes apply instantly to your 1-day safe zone calculation.
          </span>
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md shadow-emerald-600/20 active:scale-95 transition-all"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
