import React, { useState } from 'react';
import { Search, Filter, ArrowUpRight, ArrowDownRight, Plus, Check, Clock, Shield, ShieldOff, Sparkles } from 'lucide-react';
import { CategoryBudget, CategoryKey, Transaction } from '../types';

interface TransactionListProps {
  transactions: Transaction[];
  categories: CategoryBudget[];
  stealthMode: boolean;
  excludedTxIds: Set<string>;
  onAddTransaction: (newTx: Omit<Transaction, 'id'>) => void;
  onUpdateCategory: (txId: string, newCategory: CategoryKey) => void;
  onToggleSafeZoneInclusion: (txId: string) => void;
}

export const TransactionList: React.FC<TransactionListProps> = ({
  transactions,
  categories,
  stealthMode,
  excludedTxIds,
  onAddTransaction,
  onUpdateCategory,
  onToggleSafeZoneInclusion,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState<'ALL' | 'DEBIT' | 'CREDIT' | 'USER_PPE' | CategoryKey>('ALL');
  const [isAddingTx, setIsAddingTx] = useState(false);

  // New transaction form state
  const [newDesc, setNewDesc] = useState('');
  const [newAmount, setNewAmount] = useState('');
  const [newCategory, setNewCategory] = useState<CategoryKey>('Food');
  const [newType, setNewType] = useState<'DEBIT' | 'CREDIT'>('DEBIT');

  const formatCurrency = (val: number) => {
    if (stealthMode) return '₹••••';
    return `₹${val.toLocaleString('en-IN')}`;
  };

  const userPhonePeCount = transactions.filter((t) => t.source === 'user_phonepe_statement').length;

  const filteredTransactions = transactions.filter((tx) => {
    const matchesSearch =
      tx.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tx.merchant.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (tx.upiRef && tx.upiRef.toLowerCase().includes(searchQuery.toLowerCase()));

    if (!matchesSearch) return false;

    if (selectedFilter === 'ALL') return true;
    if (selectedFilter === 'DEBIT') return tx.type === 'DEBIT';
    if (selectedFilter === 'CREDIT') return tx.type === 'CREDIT';
    if (selectedFilter === 'USER_PPE') return tx.source === 'user_phonepe_statement';
    return tx.category === selectedFilter;
  });

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDesc.trim() || !newAmount) return;

    onAddTransaction({
      description: newDesc.trim(),
      merchant: newDesc.trim().slice(0, 24),
      amount: parseFloat(newAmount),
      category: newCategory,
      type: newType,
      date: new Date().toISOString().split('T')[0],
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      upiRef: `UPI/USER/${Math.floor(100000 + Math.random() * 900000)}`,
      includeInSafeZone: true,
      source: 'user_manual',
    });

    setNewDesc('');
    setNewAmount('');
    setIsAddingTx(false);
  };

  return (
    <div className="p-5 sm:p-6 rounded-3xl bg-slate-900 border border-slate-800 shadow-xl mb-8">
      {/* Header and Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <span>PhonePe UPI Transactions</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
              {filteredTransactions.length}
            </span>
            {userPhonePeCount > 0 && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">
                {userPhonePeCount} from User Statement
              </span>
            )}
          </h3>
          <p className="text-xs text-slate-400">
            Auto-categorized PhonePe UPI transactions. Click &apos;Safe Zone&apos; button to de-select any expense.
          </p>
        </div>

        <button
          onClick={() => setIsAddingTx(!isAddingTx)}
          className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-indigo-600/20 active:scale-95 transition-all self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Add / Simulate UPI Spend</span>
        </button>
      </div>

      {/* Manual / Simulated Spend Drawer */}
      {isAddingTx && (
        <form
          onSubmit={handleCreateSubmit}
          className="p-4 mb-5 rounded-2xl bg-slate-950 border border-indigo-500/30 text-xs animate-in slide-in-from-top-2 duration-200"
        >
          <div className="font-semibold text-white mb-3 flex items-center justify-between">
            <span>Record New PhonePe UPI Transaction</span>
            <span className="text-[11px] text-indigo-400">Updates 1-day safe streak live</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 mb-3">
            <div>
              <label className="block text-slate-400 mb-1">Description / Merchant</label>
              <input
                type="text"
                placeholder="e.g. Swiggy, Uber, Zomato"
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                required
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Amount (INR ₹)</label>
              <input
                type="number"
                placeholder="₹ Amount"
                value={newAmount}
                onChange={(e) => setNewAmount(e.target.value)}
                required
                min="1"
                step="any"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 placeholder-slate-600 font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Category</label>
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value as CategoryKey)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 focus:outline-none focus:border-indigo-500"
              >
                {categories.map((c) => (
                  <option key={c.key} value={c.key}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-slate-400 mb-1">Type</label>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value as 'DEBIT' | 'CREDIT')}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-100 focus:outline-none focus:border-indigo-500"
              >
                <option value="DEBIT">Debit (Expense)</option>
                <option value="CREDIT">Credit (Income)</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setIsAddingTx(false)}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold flex items-center gap-1"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Record Transaction</span>
            </button>
          </div>
        </form>
      )}

      {/* Search and Category Filter Tabs */}
      <div className="flex flex-col md:flex-row gap-3 mb-5">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search merchants, PhonePe UPI IDs, notes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Filter categories pills / scrollable container */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
          <button
            onClick={() => setSelectedFilter('ALL')}
            className={`px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-colors ${
              selectedFilter === 'ALL'
                ? 'bg-slate-100 text-slate-900 font-bold'
                : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
            }`}
          >
            All
          </button>
          {userPhonePeCount > 0 && (
            <button
              onClick={() => setSelectedFilter('USER_PPE')}
              className={`px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-colors flex items-center gap-1 ${
                selectedFilter === 'USER_PPE'
                  ? 'bg-indigo-600 text-white font-bold'
                  : 'bg-slate-950 text-indigo-400 hover:text-white border border-indigo-500/30'
              }`}
            >
              <Sparkles className="w-3 h-3" />
              <span>User PhonePe</span>
            </button>
          )}
          <button
            onClick={() => setSelectedFilter('DEBIT')}
            className={`px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-colors ${
              selectedFilter === 'DEBIT'
                ? 'bg-rose-500 text-white font-bold'
                : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
            }`}
          >
            Debits
          </button>
          <button
            onClick={() => setSelectedFilter('CREDIT')}
            className={`px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-colors ${
              selectedFilter === 'CREDIT'
                ? 'bg-emerald-500 text-white font-bold'
                : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
            }`}
          >
            Credits
          </button>
          {categories.map((c) => (
            <button
              key={c.key}
              onClick={() => setSelectedFilter(c.key)}
              className={`px-3 py-1.5 rounded-lg font-medium whitespace-nowrap transition-colors ${
                selectedFilter === c.key
                  ? 'bg-indigo-600 text-white font-bold'
                  : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              {c.name}
            </button>
          ))}
        </div>
      </div>

      {/* Transactions List */}
      <div className="divide-y divide-slate-800/80">
        {filteredTransactions.length === 0 ? (
          <div className="py-14 text-center text-slate-500 text-xs flex flex-col items-center justify-center">
            <p className="text-slate-400 font-medium mb-1">No transactions recorded yet.</p>
            <p className="text-slate-600 max-w-sm">
              Import your PhonePe statement above or click &ldquo;+ Add Transaction&rdquo; to begin tracking expenses in your 1-Day Safe Zone.
            </p>
          </div>
        ) : (
          filteredTransactions.map((tx) => {
            const isCredit = tx.type === 'CREDIT';
            const catObj = categories.find((c) => c.key === tx.category);
            const isExcludedFromSafe = excludedTxIds.has(tx.id);
            const isUserStatement = tx.source === 'user_phonepe_statement';

            return (
              <div
                key={tx.id}
                className="py-3 sm:py-3.5 flex items-center justify-between gap-3 hover:bg-slate-950/40 px-2 rounded-xl transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div
                    className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 ${
                      isCredit
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {isCredit ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                  </div>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-xs sm:text-sm font-semibold text-white truncate">
                        {tx.description}
                      </p>
                      {isUserStatement && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex-shrink-0 font-medium">
                          PhonePe UPI
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5 flex-wrap">
                      <span>{tx.date}</span>
                      {tx.time && <span>· {tx.time}</span>}
                      {tx.upiRef && (
                        <span className="font-mono text-slate-500 hidden sm:inline">
                          · {tx.upiRef}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right: Safe Zone Toggle Button, Amount & Category Selector */}
                <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
                  {/* De-select / In Safe Zone button for Debits */}
                  {!isCredit && (
                    <button
                      type="button"
                      onClick={() => onToggleSafeZoneInclusion(tx.id)}
                      className={`px-2 py-1 rounded-lg text-[10px] font-semibold flex items-center gap-1 border transition-all ${
                        !isExcludedFromSafe
                          ? 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                          : 'bg-slate-800/80 hover:bg-slate-800 text-slate-500 border-slate-700 line-through'
                      }`}
                      title={
                        !isExcludedFromSafe
                          ? 'In 1-Day Safe Zone (Click to de-select from daily limit)'
                          : 'De-selected from Safe Zone (Click to re-include in daily limit)'
                      }
                    >
                      {!isExcludedFromSafe ? (
                        <>
                          <Shield className="w-3 h-3 text-emerald-400" />
                          <span className="hidden sm:inline">Safe Zone</span>
                        </>
                      ) : (
                        <>
                          <ShieldOff className="w-3 h-3 text-slate-500" />
                          <span className="hidden sm:inline">De-selected</span>
                        </>
                      )}
                    </button>
                  )}

                  {/* Category Pill with reclassification dropdown */}
                  <div className="relative group">
                    <select
                      value={tx.category}
                      onChange={(e) => onUpdateCategory(tx.id, e.target.value as CategoryKey)}
                      className="text-[11px] font-medium bg-slate-950 border border-slate-700 hover:border-slate-600 rounded-lg px-2 py-1 text-slate-300 cursor-pointer focus:outline-none"
                      style={{ color: catObj?.color }}
                    >
                      {categories.map((c) => (
                        <option key={c.key} value={c.key}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="text-right min-w-[75px]">
                    <span
                      className={`text-xs sm:text-sm font-mono font-bold ${
                        isCredit ? 'text-emerald-400' : 'text-slate-100'
                      }`}
                    >
                      {isCredit ? '+' : '-'}{formatCurrency(tx.amount)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
