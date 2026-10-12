import React, { useState } from 'react';
import { Target, Plus, ShieldCheck, Trash2, Sparkles, Check, X, Calendar, DollarSign, Tag } from 'lucide-react';
import { SavingsGoal } from '../types';

interface SavingsGoalsSectionProps {
  goals: SavingsGoal[];
  stealthMode: boolean;
  unspentDailySafe: number;
  onAddGoal: (newGoal: Omit<SavingsGoal, 'id'>) => void;
  onDeleteGoal: (goalId: string) => void;
  onContributeToGoal: (goalId: string, amount: number) => void;
}

export const SavingsGoalsSection: React.FC<SavingsGoalsSectionProps> = ({
  goals,
  stealthMode,
  unspentDailySafe,
  onAddGoal,
  onDeleteGoal,
  onContributeToGoal,
}) => {
  const [isCreatingGoal, setIsCreatingGoal] = useState(false);
  const [goalName, setGoalName] = useState('');
  const [targetAmount, setTargetAmount] = useState('');
  const [targetDate, setTargetDate] = useState('2026-12-31');
  const [goalCategory, setGoalCategory] = useState('Emergency Fund');
  const [goalColor, setGoalColor] = useState('#10B981');
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const formatCurrency = (val: number) => {
    if (stealthMode) return '₹••••';
    return `₹${val.toLocaleString('en-IN')}`;
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!goalName.trim() || !targetAmount) return;

    onAddGoal({
      name: goalName.trim(),
      targetAmount: parseFloat(targetAmount),
      currentAmount: 0,
      targetDate,
      category: goalCategory,
      icon: 'Target',
      color: goalColor,
    });

    setGoalName('');
    setTargetAmount('');
    setIsCreatingGoal(false);
  };

  const handleDelete = (id: string) => {
    onDeleteGoal(id);
    setDeleteConfirmId(null);
  };

  const CATEGORY_COLORS: Record<string, string> = {
    'Emergency Fund': '#10B981',
    'Tech & Gadgets': '#0EA5E9',
    'Travel & Vacations': '#F97316',
    'Investments & SIP': '#8B5CF6',
    'Vehicle & Home': '#EC4899',
    'Personal & Life': '#EAB308',
  };

  return (
    <div className="p-5 sm:p-6 rounded-3xl bg-slate-900 border border-slate-800 shadow-xl mb-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <Target className="w-4 h-4" />
            </div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <span>Custom Savings Goals</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
                {goals.length}
              </span>
            </h3>
          </div>
          <p className="text-xs text-slate-400">
            Powered by your daily safe spending streak. Add, customize, or delete targets anytime.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {unspentDailySafe > 0 && (
            <div className="text-xs bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-3 py-1.5 rounded-xl font-medium flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Unspent Safe Zone: {formatCurrency(unspentDailySafe)}</span>
            </div>
          )}
          <button
            onClick={() => setIsCreatingGoal(!isCreatingGoal)}
            className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-indigo-600/20 active:scale-95 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add Custom Goal</span>
          </button>
        </div>
      </div>

      {/* Goal creation form */}
      {isCreatingGoal && (
        <form
          onSubmit={handleCreateSubmit}
          className="p-5 mb-6 rounded-2xl bg-slate-950 border border-indigo-500/30 text-xs animate-in slide-in-from-top-2 duration-200"
        >
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800">
            <span className="font-bold text-white text-sm">Add New Savings Milestone</span>
            <button
              type="button"
              onClick={() => setIsCreatingGoal(false)}
              className="text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-slate-400 mb-1 font-medium">Goal Name</label>
              <input
                type="text"
                placeholder="e.g. Bali Trip, iPhone 17, New Bike"
                value={goalName}
                onChange={(e) => setGoalName(e.target.value)}
                required
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-slate-400 mb-1 font-medium">Target Amount (INR ₹)</label>
              <input
                type="number"
                placeholder="₹ 50,000"
                value={targetAmount}
                onChange={(e) => setTargetAmount(e.target.value)}
                required
                min="500"
                step="500"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100 placeholder-slate-600 font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-slate-400 mb-1 font-medium">Target Deadline</label>
              <input
                type="date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                required
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-slate-400 mb-1 font-medium">Category</label>
              <select
                value={goalCategory}
                onChange={(e) => {
                  setGoalCategory(e.target.value);
                  setGoalColor(CATEGORY_COLORS[e.target.value] || '#10B981');
                }}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-slate-100 focus:outline-none focus:border-indigo-500"
              >
                {Object.keys(CATEGORY_COLORS).map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-2">
            <button
              type="button"
              onClick={() => setIsCreatingGoal(false)}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold flex items-center gap-1.5 shadow"
            >
              <Check className="w-4 h-4" />
              <span>Save &amp; Track Goal</span>
            </button>
          </div>
        </form>
      )}

      {/* Goals Cards Grid */}
      {goals.length === 0 ? (
        <div className="p-8 text-center rounded-2xl bg-slate-950/40 border border-slate-800">
          <p className="text-slate-400 text-xs mb-3">No savings goals yet. Create one to turn your safe spending streak into real assets!</p>
          <button
            onClick={() => setIsCreatingGoal(true)}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold"
          >
            Create Your First Savings Goal
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {goals.map((goal) => {
            const progressPercent = Math.min(100, Math.round((goal.currentAmount / goal.targetAmount) * 100));
            const remainingAmount = Math.max(0, goal.targetAmount - goal.currentAmount);
            const isDeleting = deleteConfirmId === goal.id;

            return (
              <div
                key={goal.id}
                className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col justify-between group relative"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-3">
                    <div>
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                        {goal.category}
                      </span>
                      <h4 className="text-sm font-bold text-white mt-0.5">{goal.name}</h4>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <div
                        className="p-1.5 rounded-lg text-xs font-bold"
                        style={{ backgroundColor: `${goal.color}15`, color: goal.color }}
                      >
                        {progressPercent}%
                      </div>

                      {/* Delete Goal Button */}
                      {isDeleting ? (
                        <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-rose-500/40 animate-in fade-in">
                          <button
                            onClick={() => handleDelete(goal.id)}
                            className="px-1.5 py-0.5 rounded bg-rose-600 text-white text-[10px] font-bold hover:bg-rose-500"
                            title="Confirm delete"
                          >
                            Delete
                          </button>
                          <button
                            onClick={() => setDeleteConfirmId(null)}
                            className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] hover:bg-slate-700"
                          >
                            ✕
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setDeleteConfirmId(goal.id)}
                          className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                          title="Delete this savings goal"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="flex items-baseline justify-between mb-2">
                    <span className="text-lg font-bold font-mono text-white">
                      {formatCurrency(goal.currentAmount)}
                    </span>
                    <span className="text-xs text-slate-500 font-mono">
                      / {formatCurrency(goal.targetAmount)}
                    </span>
                  </div>

                  {/* Progress bar */}
                  <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden mb-3">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${progressPercent}%`,
                        backgroundColor: goal.color,
                      }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 mb-4">
                    <span>Remaining: {formatCurrency(remainingAmount)}</span>
                    <span>Due: {goal.targetDate}</span>
                  </div>
                </div>

                {/* Action: Transfer Safe Surplus or Quick Boost */}
                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                  <button
                    onClick={() => onContributeToGoal(goal.id, 500)}
                    className="w-full py-2 px-3 rounded-xl bg-slate-800/80 hover:bg-slate-800 text-slate-200 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <span>+₹500 Boost</span>
                  </button>
                  {unspentDailySafe > 0 && (
                    <button
                      onClick={() => onContributeToGoal(goal.id, unspentDailySafe)}
                      title={`Deposit unspent ₹${unspentDailySafe} from today's safe zone`}
                      className="py-2 px-3 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 text-xs font-semibold whitespace-nowrap transition-colors"
                    >
                      Deposit +₹{unspentDailySafe}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
