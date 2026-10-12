import React, { useState, useEffect, useMemo } from 'react';
import {
  INITIAL_CATEGORIES,
  INITIAL_TRANSACTIONS,
  INITIAL_SAFE_ZONE_CONFIG,
  INITIAL_SAVINGS_GOALS,
  INITIAL_SMART_ALERTS,
} from './data/initialData';
import {
  Transaction,
  CategoryBudget,
  SafeZoneConfig,
  SavingsGoal,
  SmartAlert,
  CategoryKey,
} from './types';
import { HeaderNav } from './components/HeaderNav';
import { SafeZoneBanner } from './components/SafeZoneBanner';
import { DashboardCharts } from './components/DashboardCharts';
import { TransactionList } from './components/TransactionList';
import { SavingsGoalsSection } from './components/SavingsGoalsSection';
import { StatementUploadModal } from './components/StatementUploadModal';
import { BudgetManagerModal } from './components/BudgetManagerModal';
import { SafeZoneManagerModal } from './components/SafeZoneManagerModal';
import { SmartAlertsPanel } from './components/SmartAlertsPanel';
import { BiometricLockModal } from './components/BiometricLockModal';
import { PushNotificationToast } from './components/PushNotificationToast';
import { Sparkles, FileText, CheckCircle2, Shield, UploadCloud, RefreshCw, AlertCircle } from 'lucide-react';

export default function App() {
  // Theme & Privacy
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [stealthMode, setStealthMode] = useState(false);
  const [isLocked, setIsLocked] = useState(false);
  const [savedPin] = useState('1234');

  // Active Statement Source Tracking (Initialized to empty until user imports)
  const [statementInfo, setStatementInfo] = useState({
    fileName: 'No Statement Imported',
    isUserStatement: false,
    count: 0,
    importTimestamp: null as string | null,
  });

  // Core Financial Data (Initialized to 0 until statement is imported)
  const [transactions, setTransactions] = useState<Transaction[]>(INITIAL_TRANSACTIONS);
  const [budgets, setBudgets] = useState<CategoryBudget[]>(INITIAL_CATEGORIES);
  const [safeZone, setSafeZone] = useState<SafeZoneConfig>(INITIAL_SAFE_ZONE_CONFIG);
  const [goals, setGoals] = useState<SavingsGoal[]>(INITIAL_SAVINGS_GOALS);
  const [alerts, setAlerts] = useState<SmartAlert[]>(INITIAL_SMART_ALERTS);
  const [aiInsights, setAiInsights] = useState<string[]>([
    'Awaiting PhonePe statement import. AI will analyze merchant patterns, frequent UPI transfers, and dining velocity.',
    'Once imported, your monthly safe spending cap will be divided across existing categories with tailored saving limits.',
    'Daily safe spending zone will prevent budget overruns with real-time alerts before you breach daily caps.',
  ]);

  // Safe Zone De-selection state (User can de-select individual transactions or entire categories)
  const [excludedTxIds, setExcludedTxIds] = useState<Set<string>>(new Set());
  const [excludedCategories, setExcludedCategories] = useState<Set<CategoryKey>>(
    new Set(['Transfers', 'Investments'])
  );

  // Modals & Panels
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isBudgetOpen, setIsBudgetOpen] = useState(false);
  const [isSafeZoneOpen, setIsSafeZoneOpen] = useState(false);
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);
  const [pushNotification, setPushNotification] = useState<{ id: string; title: string; body: string } | null>(null);

  // Sync category spent amounts dynamically with current transactions
  const categoriesWithSpent = useMemo(() => {
    const sums: Record<CategoryKey, number> = {
      Food: 0,
      Entertainment: 0,
      Utilities: 0,
      'Health Care': 0,
      Shopping: 0,
      Subscriptions: 0,
      Transfers: 0,
      Investments: 0,
    };

    transactions.forEach((tx) => {
      if (tx.type === 'DEBIT') {
        const cat = tx.category as CategoryKey;
        if (sums[cat] !== undefined) {
          sums[cat] += tx.amount;
        } else {
          sums['Transfers'] += tx.amount;
        }
      }
    });

    return budgets.map((b) => ({
      ...b,
      spent: sums[b.key] || 0,
    }));
  }, [transactions, budgets]);

  // Date format
  const todayDateStr = useMemo(() => new Date().toISOString().split('T')[0], []);

  // Compute today's active spend for the 1-Day Safe Zone (respecting de-selected items!)
  const todaySpentCalculated = useMemo(() => {
    return transactions
      .filter((t) => {
        if (t.type !== 'DEBIT' || t.date !== todayDateStr) return false;
        if (excludedTxIds.has(t.id)) return false;
        if (excludedCategories.has(t.category as CategoryKey)) return false;
        return true;
      })
      .reduce((sum, t) => sum + t.amount, 0);
  }, [transactions, todayDateStr, excludedTxIds, excludedCategories]);

  // Total month spent calculation
  const totalMonthSpentCalculated = useMemo(() => {
    return transactions
      .filter((t) => t.type === 'DEBIT')
      .reduce((sum, t) => sum + t.amount, 0);
  }, [transactions]);

  // Update Safe Zone configuration state whenever today's spend or month's spend changes
  useEffect(() => {
    setSafeZone((prev) => {
      const updatedHistory = [...prev.history];
      if (updatedHistory.length > 0) {
        const lastIndex = updatedHistory.length - 1;
        updatedHistory[lastIndex] = {
          ...updatedHistory[lastIndex],
          spent: todaySpentCalculated,
          limit: prev.dailySafeLimit,
          status: todaySpentCalculated > prev.dailySafeLimit ? 'over' : 'safe',
        };
      }
      return {
        ...prev,
        todaySpent: todaySpentCalculated,
        monthSpent: totalMonthSpentCalculated,
        history: updatedHistory,
      };
    });
  }, [todaySpentCalculated, totalMonthSpentCalculated]);

  // Push notification helper
  const triggerPushBanner = (title: string, body: string) => {
    const notif = {
      id: `notif_${Date.now()}`,
      title,
      body,
    };
    setPushNotification(notif);

    setAlerts((prev) => [
      {
        id: `alt_push_${Date.now()}`,
        type: 'proximity',
        title,
        message: body,
        timestamp: 'Just now',
        read: false,
      },
      ...prev,
    ]);
  };

  // Safe Zone De-selection Toggle Handlers
  const handleToggleTxSafeZone = (txId: string) => {
    setExcludedTxIds((prev) => {
      const next = new Set(prev);
      const isCurrentlyExcluded = next.has(txId);
      if (isCurrentlyExcluded) {
        next.delete(txId);
        triggerPushBanner('🛡️ Re-included in Safe Zone', 'Expense is now counted in your 1-day safe limit.');
      } else {
        next.add(txId);
        triggerPushBanner('⊘ De-selected from Safe Zone', 'Expense is shielded from your 1-day safe limit.');
      }
      return next;
    });
  };

  const handleToggleCategorySafeZone = (catKey: CategoryKey) => {
    setExcludedCategories((prev) => {
      const next = new Set(prev);
      const isCurrentlyExcluded = next.has(catKey);
      if (isCurrentlyExcluded) {
        next.delete(catKey);
        triggerPushBanner(`🛡️ ${catKey} Category Included`, `${catKey} expenses now count toward safe zone.`);
      } else {
        next.add(catKey);
        triggerPushBanner(`⊘ ${catKey} Category De-selected`, `${catKey} expenses are shielded from daily safe zone.`);
      }
      return next;
    });
  };

  // Handler: Add transaction (simulated or real)
  const handleAddTransaction = (newTxData: Omit<Transaction, 'id'>) => {
    const newTx: Transaction = {
      ...newTxData,
      id: `tx_${Date.now()}`,
      aiSuggestedCategory: newTxData.category,
    };

    setTransactions((prev) => [newTx, ...prev]);

    // Check if new spend exceeds safe limit
    if (newTx.type === 'DEBIT' && newTx.date === todayDateStr && !excludedCategories.has(newTx.category)) {
      const nextTodaySpent = todaySpentCalculated + newTx.amount;
      if (nextTodaySpent > safeZone.dailySafeLimit) {
        triggerPushBanner(
          '🚨 1-Day Safe Zone Exceeded!',
          `You spent ₹${newTx.amount} on ${newTx.description}. Today's total is ₹${nextTodaySpent}, exceeding your ₹${safeZone.dailySafeLimit} safe limit.`
        );
      } else if (nextTodaySpent >= safeZone.dailySafeLimit * 0.8) {
        triggerPushBanner(
          '⚠️ 80% Safe Zone Proximity Warning',
          `Heads up! Today's spend is ₹${nextTodaySpent} of ₹${safeZone.dailySafeLimit}. Only ₹${safeZone.dailySafeLimit - nextTodaySpent} remaining in safe zone.`
        );
      }
    }
  };

  // Quick simulate spend button
  const handleQuickSpend = (amount: number, description: string) => {
    handleAddTransaction({
      description: `Paid via PhonePe UPI - ${description}`,
      merchant: description,
      amount,
      category: 'Food',
      type: 'DEBIT',
      date: todayDateStr,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      upiRef: `UPI/PPE/${Math.floor(100000 + Math.random() * 900000)}`,
      includeInSafeZone: true,
      source: 'user_phonepe_statement',
    });
  };

  // Handler: Update transaction category
  const handleUpdateCategory = (txId: string, newCategory: CategoryKey) => {
    setTransactions((prev) =>
      prev.map((t) => (t.id === txId ? { ...t, category: newCategory } : t))
    );
  };

  // Handler: Statement parsed, reviewed, and recorded (Replaces existing statement completely)
  const handleStatementLoaded = (
    newTransactions: Transaction[],
    newBudgets?: CategoryBudget[],
    dailySafe?: number,
    newHabits?: string[],
    loadedFileName?: string,
    userMonthlyBudget?: number,
    userSavingsLimit?: number
  ) => {
    // 1. Tag all new transactions as user PhonePe transactions
    const taggedTransactions = newTransactions.map((t) => ({
      ...t,
      source: 'user_phonepe_statement',
      includeInSafeZone: true,
    }));

    // 2. Clear old state and set new transactions
    setTransactions(taggedTransactions);
    setExcludedTxIds(new Set()); // Reset any exclusion overrides from old statement
    
    setStatementInfo({
      fileName: loadedFileName || 'PhonePe_Statement.pdf',
      isUserStatement: true,
      count: taggedTransactions.length,
      importTimestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    });

    // 3. Update category budgets based on new statement
    if (newBudgets && newBudgets.length > 0) {
      setBudgets(newBudgets);
    }

    // 4. Calculate safe monthly cap & daily safe limit based on new statement
    const resolvedMonthlyBudget = userMonthlyBudget ?? 3000;
    const resolvedSavingsLimit = userSavingsLimit ?? 0;
    const safeMonthlyCap = Math.max(0, resolvedMonthlyBudget - resolvedSavingsLimit);
    const computedDaily = dailySafe !== undefined && dailySafe > 0 ? dailySafe : 100;

    // 5. Compute daily history from the newly uploaded statement
    const newHistoryMap: Record<string, number> = {};
    taggedTransactions.forEach((t) => {
      if (t.type === 'DEBIT') {
        newHistoryMap[t.date] = (newHistoryMap[t.date] || 0) + t.amount;
      }
    });

    const datesList: { date: string; dayLabel: string }[] = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const dStr = d.toISOString().split('T')[0];
      const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const label = i === 0 ? 'Today' : i === 1 ? 'Yesterday' : dayNames[d.getDay()];
      datesList.push({ date: dStr, dayLabel: label });
    }

    const calculatedHistory = datesList.map(({ date, dayLabel }) => {
      const spent = newHistoryMap[date] || 0;
      return {
        date,
        dayLabel,
        spent,
        limit: computedDaily,
        status: (spent > computedDaily ? 'over' : 'safe') as 'safe' | 'over',
      };
    });

    const calculatedMonthSpent = taggedTransactions
      .filter((t) => t.type === 'DEBIT')
      .reduce((sum, t) => sum + t.amount, 0);

    const calculatedTodaySpent = taggedTransactions
      .filter((t) => t.type === 'DEBIT' && t.date === todayDateStr)
      .reduce((sum, t) => sum + t.amount, 0);

    setSafeZone({
      dailySafeLimit: computedDaily,
      todaySpent: calculatedTodaySpent,
      monthlyBudget: resolvedMonthlyBudget,
      savingsLimit: resolvedSavingsLimit,
      aiSuggestedSavingsLimit: resolvedSavingsLimit,
      monthlySafeLimit: safeMonthlyCap,
      monthSpent: calculatedMonthSpent,
      history: calculatedHistory,
    });

    if (newHabits && newHabits.length > 0) {
      setAiInsights(newHabits);
    }

    triggerPushBanner(
      '✅ New PhonePe Statement Imported',
      `Replaced previous statement with ${taggedTransactions.length} transactions from "${loadedFileName || 'statement'}". All limits recalculated.`
    );
  };

  // Handler: Reset/Clear to Zero State
  const handleResetToZero = () => {
    setTransactions([]);
    setBudgets(INITIAL_CATEGORIES);
    setSafeZone(INITIAL_SAFE_ZONE_CONFIG);
    setExcludedTxIds(new Set());
    setStatementInfo({
      fileName: 'No Statement Imported',
      isUserStatement: false,
      count: 0,
      importTimestamp: null,
    });
    setAiInsights([
      'Awaiting PhonePe statement import. AI will analyze merchant patterns, frequent UPI transfers, and dining velocity.',
      'Once imported, your monthly safe spending cap will be divided across existing categories with tailored saving limits.',
      'Daily safe spending zone will prevent budget overruns with real-time alerts before you breach daily caps.',
    ]);
    triggerPushBanner('🔄 Reset to Zero State', 'All UI values cleared back to zero awaiting statement import.');
  };

  // Handler: Save custom budgets from modal
  const handleSaveBudgets = (
    updatedBudgets: CategoryBudget[],
    updatedMonthlyBudget: number,
    updatedSavingsLimit: number,
    updatedDailySafe: number
  ) => {
    setBudgets(updatedBudgets);
    const updatedMonthlySafe = Math.max(0, updatedMonthlyBudget - updatedSavingsLimit);

    setSafeZone((prev) => ({
      ...prev,
      monthlyBudget: updatedMonthlyBudget,
      savingsLimit: updatedSavingsLimit,
      monthlySafeLimit: updatedMonthlySafe,
      dailySafeLimit: updatedDailySafe,
    }));

    triggerPushBanner(
      '🎯 Budget & Safe Zone Saved',
      `Monthly Safe Limit: ₹${updatedMonthlySafe.toLocaleString('en-IN')}, 1-Day Safe Zone: ₹${updatedDailySafe.toLocaleString('en-IN')}/day.`
    );
  };

  // Handler: Add savings goal
  const handleAddGoal = (newGoalData: Omit<SavingsGoal, 'id'>) => {
    const newGoal: SavingsGoal = {
      ...newGoalData,
      id: `goal_${Date.now()}`,
    };
    setGoals((prev) => [...prev, newGoal]);
    triggerPushBanner('🎯 New Goal Created', `Created savings goal: ${newGoal.name}`);
  };

  // Handler: Delete savings goal
  const handleDeleteGoal = (goalId: string) => {
    const goalToRemove = goals.find((g) => g.id === goalId);
    setGoals((prev) => prev.filter((g) => g.id !== goalId));
    triggerPushBanner(
      '🗑️ Savings Goal Removed',
      `Deleted "${goalToRemove?.name || 'Goal'}" from your targets.`
    );
  };

  // Handler: Contribute to savings goal
  const handleContributeGoal = (goalId: string, amount: number) => {
    setGoals((prev) =>
      prev.map((g) => (g.id === goalId ? { ...g, currentAmount: g.currentAmount + amount } : g))
    );
    triggerPushBanner(
      '🎉 Milestone Boosted!',
      `Deposited ₹${amount.toLocaleString('en-IN')} toward your goal from your safe daily reserve.`
    );
  };

  const unreadAlertCount = alerts.filter((a) => !a.read).length;
  const unspentDailySafe = Math.max(0, safeZone.dailySafeLimit - safeZone.todaySpent);

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-900'} antialiased selection:bg-indigo-500 selection:text-white`}>
      {/* Biometric Security Lock Overlay */}
      <BiometricLockModal
        isOpen={isLocked}
        onUnlock={() => setIsLocked(false)}
        savedPin={savedPin}
        stealthMode={stealthMode}
        onToggleStealth={() => setStealthMode(!stealthMode)}
      />

      {/* Push Notification Banner Simulator */}
      <PushNotificationToast
        notification={pushNotification}
        onDismiss={() => setPushNotification(null)}
      />

      {/* Sticky Header */}
      <HeaderNav
        isDarkMode={isDarkMode}
        onToggleTheme={() => setIsDarkMode(!isDarkMode)}
        stealthMode={stealthMode}
        onToggleStealth={() => setStealthMode(!stealthMode)}
        onLockApp={() => setIsLocked(true)}
        onOpenUpload={() => setIsUploadOpen(true)}
        onOpenBudgets={() => setIsBudgetOpen(true)}
        onOpenSafeZone={() => setIsSafeZoneOpen(true)}
        onOpenAlerts={() => setIsAlertsOpen(true)}
        unreadAlertCount={unreadAlertCount}
        safeZone={safeZone}
      />

      {/* Main Content Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {/* Welcome / Active PhonePe Statement Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
              Wispend Financial Command
            </h1>
            <div className="flex items-center gap-2 mt-1 text-xs text-slate-400">
              {statementInfo.isUserStatement ? (
                <span className="text-emerald-400 font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Active: {statementInfo.fileName} ({statementInfo.count} Txns)
                </span>
              ) : (
                <span className="text-amber-400 font-semibold flex items-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  Awaiting PhonePe Statement Import (UI values at 0)
                </span>
              )}
              {statementInfo.importTimestamp && (
                <>
                  <span>·</span>
                  <span className="text-slate-400">Loaded at {statementInfo.importTimestamp}</span>
                </>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {statementInfo.isUserStatement && (
              <button
                onClick={handleResetToZero}
                className="px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs font-semibold text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition-colors"
                title="Clear current data back to zero"
              >
                <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
                <span>Reset to Zero</span>
              </button>
            )}
            <button
              onClick={() => setIsUploadOpen(true)}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center gap-2 shadow-md shadow-indigo-600/20 active:scale-95 transition-all"
            >
              <UploadCloud className="w-4 h-4 text-white" />
              <span>{statementInfo.isUserStatement ? 'Import New Statement (Replaces Old)' : 'Import PhonePe Statement'}</span>
            </button>
            <button
              onClick={() => setIsBudgetOpen(true)}
              className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-indigo-500/30 text-xs font-semibold text-slate-200 active:scale-95 transition-all"
            >
              <span>Manage Monthly Safe Cap &amp; AI Splits</span>
            </button>
          </div>
        </div>

        {/* 1. Safe Zone UI Banner (1-Day Safe Zone UI + Monthly Safe Zone UI side-by-side) */}
        <SafeZoneBanner
          safeZone={safeZone}
          stealthMode={stealthMode}
          onSimulateSpend={handleQuickSpend}
          onOpenBudgetModal={() => setIsBudgetOpen(true)}
          onOpenSafeZoneModal={() => setIsSafeZoneOpen(true)}
        />

        {/* 2. Monthly Visualizations & Multi-Format Daily Velocity Charts (Bar, Line, Pie, Table) */}
        <DashboardCharts
          categories={categoriesWithSpent}
          safeZone={safeZone}
          transactions={transactions}
          stealthMode={stealthMode}
          onOpenBudgetModal={() => setIsBudgetOpen(true)}
        />

        {/* 4. Custom Savings Goals (Add & Delete Supported) */}
        <SavingsGoalsSection
          goals={goals}
          stealthMode={stealthMode}
          unspentDailySafe={unspentDailySafe}
          onAddGoal={handleAddGoal}
          onDeleteGoal={handleDeleteGoal}
          onContributeToGoal={handleContributeGoal}
        />

        {/* 5. PhonePe UPI Transactions List with De-selection & Filtering */}
        <TransactionList
          transactions={transactions}
          categories={categoriesWithSpent}
          stealthMode={stealthMode}
          excludedTxIds={excludedTxIds}
          onAddTransaction={handleAddTransaction}
          onUpdateCategory={handleUpdateCategory}
          onToggleSafeZoneInclusion={handleToggleTxSafeZone}
        />
      </main>

      {/* Modals */}
      <StatementUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onStatementLoaded={handleStatementLoaded}
      />

      <BudgetManagerModal
        isOpen={isBudgetOpen}
        onClose={() => setIsBudgetOpen(false)}
        categories={categoriesWithSpent}
        monthlyBudget={safeZone.monthlyBudget}
        savingsLimit={safeZone.savingsLimit}
        aiSuggestedSavingsLimit={safeZone.aiSuggestedSavingsLimit}
        currentDailySafeLimit={safeZone.dailySafeLimit}
        onSaveBudgets={handleSaveBudgets}
      />

      {/* 1-Day Safe Zone De-selection Modal */}
      <SafeZoneManagerModal
        isOpen={isSafeZoneOpen}
        onClose={() => setIsSafeZoneOpen(false)}
        transactions={transactions}
        categories={categoriesWithSpent}
        dailyLimit={safeZone.dailySafeLimit}
        excludedTxIds={excludedTxIds}
        excludedCategories={excludedCategories}
        onToggleTxInclusion={handleToggleTxSafeZone}
        onToggleCategoryInclusion={handleToggleCategorySafeZone}
        todayDateStr={todayDateStr}
      />

      <SmartAlertsPanel
        alerts={alerts}
        isOpen={isAlertsOpen}
        onClose={() => setIsAlertsOpen(false)}
        onMarkAllRead={() => setAlerts((prev) => prev.map((a) => ({ ...a, read: true })))}
        onSimulatePushBanner={triggerPushBanner}
      />
    </div>
  );
}
