import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Loader2,
  X,
  ArrowRight,
  Shield,
  Copy,
  Trash2,
  Plus,
  Check,
  Edit3,
  BarChart3,
  Download,
  ArrowLeft,
  DollarSign,
  PiggyBank,
  Sliders,
  AlertTriangle,
} from 'lucide-react';
import { Transaction, CategoryBudget, CategoryKey } from '../types';
import { calculateAiCategoryDivision, evaluateSafeCapStatus } from '../utils/budgetCalculations';

interface StatementUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onStatementLoaded: (
    transactions: Transaction[],
    newBudgets?: CategoryBudget[],
    dailySafeLimit?: number,
    habitsInsights?: string[],
    fileName?: string,
    userMonthlyBudget?: number,
    userSavingsLimit?: number
  ) => void;
}

const CATEGORIES_LIST: CategoryKey[] = [
  'Food',
  'Entertainment',
  'Utilities',
  'Health Care',
  'Shopping',
  'Subscriptions',
  'Transfers',
  'Investments',
];

const SAMPLE_PASTE_PHONEPE_TEXT = `PhonePe Transaction Statement
Mobile Number: 9876543210
Statement Period: 01 Oct 2026 - 12 Oct 2026

Date & Time, Transaction Details, Type, Amount, Transaction ID, UTR
12 Oct 2026, 01:10 PM, Paid to Swiggy - Salad Days, DEBIT, ₹420.00, T26101213109923, 428912345678
11 Oct 2026, 08:30 PM, Paid to Zomato - Meghana Foods, DEBIT, ₹920.00, T26101120301145, 428912345679
10 Oct 2026, 06:15 PM, Paid to Decathlon Sports India, DEBIT, ₹1850.00, T26101018152233, 428912345680
09 Oct 2026, 02:00 PM, Paid to Haldirams Sweets, DEBIT, ₹480.00, T26100914008899, 428912345681
08 Oct 2026, 05:15 PM, Received from Rohit Sharma Dinner Split, CREDIT, ₹1650.00, T26100817154455, 428912345682
07 Oct 2026, 09:00 AM, Paid to Blue Tokai Coffee Roasters, DEBIT, ₹340.00, T26100709001122, 428912345683
06 Oct 2026, 07:30 PM, Paid to Blinkit Grocery Delivery, DEBIT, ₹1450.00, T26100619307788, 428912345684
05 Oct 2026, 11:00 AM, Paid to Apollo Pharmacy Medicines, DEBIT, ₹1420.00, T26100511003344, 428912345685
04 Oct 2026, 03:30 PM, Paid to Amazon Pay India, DEBIT, ₹2499.00, T26100415306677, 428912345686
03 Oct 2026, 02:30 PM, Paid to BESCOM Electricity Bill, DEBIT, ₹2340.00, T26100314309900, 428912345687
02 Oct 2026, 10:00 AM, Paid to Zerodha Broking Ltd Nifty SIP, DEBIT, ₹15000.00, T26100210001122, 428912345688
02 Oct 2026, 09:00 AM, Transfer to Landlord Ramesh Rao Apartment Rent, DEBIT, ₹26000.00, T26100209003344, 428912345689
01 Oct 2026, 09:30 AM, Monthly Salary Credit from TechCorp Ltd, CREDIT, ₹118000.00, T26100109305566, 428912345690`;

type ImportStep = 'upload' | 'reading' | 'review' | 'report';

export const StatementUploadModal: React.FC<StatementUploadModalProps> = ({
  isOpen,
  onClose,
  onStatementLoaded,
}) => {
  const [currentStep, setCurrentStep] = useState<ImportStep>('upload');
  const [activeTab, setActiveTab] = useState<'upload' | 'paste' | 'sample'>('upload');
  const [processingStage, setProcessingStage] = useState('');
  const [pasteContent, setPasteContent] = useState('');
  const [activeFileName, setActiveFileName] = useState('PhonePe_Statement.pdf');
  const [errorMsg, setErrorMsg] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Extracted transactions for the "Review" step
  const [extractedTransactions, setExtractedTransactions] = useState<Transaction[]>([]);
  const [aiHabits, setAiHabits] = useState<string[] | undefined>(undefined);
  const [reviewSearch, setReviewSearch] = useState('');

  // USER INPUT FOR MONTHLY BUDGET during review stage (Initially 3,000, user can change)
  const [userMonthlyBudget, setUserMonthlyBudget] = useState<number>(3000);

  // AI SUGGESTION FOR SAVING LIMIT (user editable)
  const [userSavingsLimit, setUserSavingsLimit] = useState<number>(0);
  const [aiSavingsSuggestion, setAiSavingsSuggestion] = useState<number>(0);

  // 1-DAY SAFE LIMIT DEPENDING ON MONTHLY SAFE SPENDING CAP (Default: 100 rupees, user editable at any time)
  const [userDailySafeLimit, setUserDailySafeLimit] = useState<number>(100);

  // CATEGORY ALLOCATION (Divided based on monthly safe spending cap by AI, sum strictly equals safe cap)
  const [categoryAllocations, setCategoryAllocations] = useState<Record<CategoryKey, number>>(() =>
    calculateAiCategoryDivision(3000)
  );

  const [showBudgetDivider, setShowBudgetDivider] = useState(true);

  if (!isOpen) return null;

  const handleReset = () => {
    setCurrentStep('upload');
    setExtractedTransactions([]);
    setErrorMsg('');
    setPasteContent('');
  };

  // Helper to calculate AI division of monthly safe spending cap across existing categories
  // GUARANTEED: sum of AI category division allocation strictly equals monthly safe cap!
  const divideBudgetAcrossCategories = (monthlyTotal: number, savingsTarget: number) => {
    // Monthly safe spending cap = monthly budget - savings limit
    const monthlySafeSpendingCap = Math.max(0, monthlyTotal - savingsTarget);
    
    // Auto-update daily safe limit depending on monthly safe spending cap (100 if 3000, or cap / 30)
    const computedDaily = monthlySafeSpendingCap === 3000 ? 100 : Math.max(0, Math.round(monthlySafeSpendingCap / 30 / 10) * 10);
    setUserDailySafeLimit(computedDaily);

    // AI category allocation summary is divided based on the monthly safe spending cap
    const newAllocations = calculateAiCategoryDivision(monthlySafeSpendingCap);
    setCategoryAllocations(newAllocations);
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setActiveFileName(file.name);
    setErrorMsg('');
    setCurrentStep('reading');
    setProcessingStage(`Reading ${file.name}...`);

    try {
      const reader = new FileReader();

      if (file.name.endsWith('.pdf')) {
        reader.onload = async () => {
          const base64 = (reader.result as string).split(',')[1];
          await processServerStatement({ base64Data: base64, fileName: file.name });
        };
        reader.readAsDataURL(file);
      } else {
        reader.onload = async () => {
          const text = reader.result as string;
          await processServerStatement({ rawText: text, fileName: file.name });
        };
        reader.readAsText(file);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to read statement file');
      setCurrentStep('upload');
    }
  };

  const processServerStatement = async (payload: { base64Data?: string; rawText?: string; fileName?: string }) => {
    try {
      setProcessingStage('Extracting PhonePe UPI transactions & UTR details...');
      const parseRes = await fetch('/api/parse-statement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const parseData = await parseRes.json();
      if (!parseRes.ok || !parseData.success) {
        throw new Error(parseData.error || 'Failed to parse PhonePe statement');
      }

      setProcessingStage('AI categorizing transactions & computing savings recommendations...');
      
      const aiRes = await fetch('/api/ai-budget-suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transactions: parseData.transactions,
          userMonthlyIncome: userMonthlyBudget,
        }),
      });

      if (aiRes.ok) {
        const aiData = await aiRes.json();
        setAiHabits(aiData.habitsInsights);
        if (aiData.income) {
          setUserMonthlyBudget(aiData.income);
          const aiSav = Math.round((aiData.income * 0.25) / 1000) * 1000;
          setAiSavingsSuggestion(aiSav);
          setUserSavingsLimit(aiSav);
          divideBudgetAcrossCategories(aiData.income, aiSav);
        }
      }

      // Populate transactions with AI category suggestion initially
      const formattedTransactions = parseData.transactions.map((t: any) => ({
        ...t,
        aiSuggestedCategory: t.category, // Initially given by AI
        category: t.category, // Current category (user can edit)
        source: 'user_phonepe_statement',
        includeInSafeZone: true,
      }));

      setExtractedTransactions(formattedTransactions);
      setActiveFileName(payload.fileName || 'PhonePe_Statement.pdf');
      setCurrentStep('review');
    } catch (err: any) {
      setErrorMsg(err.message || 'Processing failed. You can paste statement text directly.');
      setCurrentStep('upload');
    }
  };

  const handleLoadSample = async () => {
    setCurrentStep('reading');
    setErrorMsg('');
    setProcessingStage('Reading authentic PhonePe UPI statement (Oct 2026)...');

    try {
      const res = await fetch('/api/sample-statement');
      const data = await res.json();
      if (!res.ok || !data.success) {
        throw new Error(data.error || 'Failed to load sample');
      }

      setProcessingStage('AI categorizing transactions & habit suggestions...');
      const aiRes = await fetch('/api/ai-budget-suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transactions: data.transactions,
          userMonthlyIncome: 115000,
        }),
      });

      if (aiRes.ok) {
        const aiData = await aiRes.json();
        setAiHabits(aiData.habitsInsights);
      }

      const formattedTransactions = data.transactions.map((t: any) => ({
        ...t,
        aiSuggestedCategory: t.category,
        category: t.category,
        source: 'user_phonepe_statement',
        includeInSafeZone: true,
      }));

      setExtractedTransactions(formattedTransactions);
      setActiveFileName('PhonePe_Statement_Oct2026.pdf');
      setCurrentStep('review');
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load sample statement');
      setCurrentStep('upload');
    }
  };

  const handlePasteSubmit = () => {
    if (!pasteContent.trim()) {
      setErrorMsg('Please paste your PhonePe statement text or transaction lines.');
      return;
    }
    setCurrentStep('reading');
    processServerStatement({ rawText: pasteContent, fileName: 'User_PhonePe_Statement.txt' });
  };

  // Review Table Handlers
  const handleUpdateTxField = (id: string, field: keyof Transaction, val: any) => {
    setExtractedTransactions((prev) =>
      prev.map((t) => (t.id === id ? { ...t, [field]: val } : t))
    );
  };

  const handleDeleteExtractedTx = (id: string) => {
    setExtractedTransactions((prev) => prev.filter((t) => t.id !== id));
  };

  const handleAddManualRow = () => {
    const newRow: Transaction = {
      id: `tx_manual_${Date.now()}`,
      date: new Date().toISOString().split('T')[0],
      time: '12:00 PM',
      description: 'New PhonePe Transaction',
      merchant: 'Merchant',
      type: 'DEBIT',
      amount: 100,
      category: 'Food',
      aiSuggestedCategory: 'Food',
      upiRef: `UPI/PPE/${Math.floor(100000 + Math.random() * 900000)}`,
      includeInSafeZone: true,
      source: 'user_phonepe_statement',
    };
    setExtractedTransactions((prev) => [newRow, ...prev]);
  };

  // Handlers for Monthly Budget & Savings inputs in Review Stage
  const handleBudgetChange = (newBudget: number) => {
    setUserMonthlyBudget(newBudget);
    const newAiSavings = Math.round((newBudget * 0.25) / 1000) * 1000;
    setAiSavingsSuggestion(newAiSavings);
    setUserSavingsLimit(newAiSavings);
    divideBudgetAcrossCategories(newBudget, newAiSavings);
  };

  const handleSavingsChange = (newSavings: number) => {
    setUserSavingsLimit(newSavings);
    divideBudgetAcrossCategories(userMonthlyBudget, newSavings);
  };

  const handleCategoryAllocationChange = (cat: CategoryKey, val: number) => {
    setCategoryAllocations((prev) => ({
      ...prev,
      [cat]: Math.max(0, val),
    }));
  };

  // STEP 3: RECORD
  const handleConfirmRecord = () => {
    const CATEGORY_META: Record<CategoryKey, { name: string; color: string; iconName: string }> = {
      Food: { name: 'Food & Dining', color: '#F97316', iconName: 'UtensilsCrossed' },
      Transfers: { name: 'Transfers & Rent', color: '#14B8A6', iconName: 'ArrowRightLeft' },
      Shopping: { name: 'Shopping', color: '#EAB308', iconName: 'ShoppingBag' },
      Utilities: { name: 'Utilities & Bills', color: '#0EA5E9', iconName: 'Zap' },
      Investments: { name: 'Investments & SIP', color: '#10B981', iconName: 'TrendingUp' },
      'Health Care': { name: 'Health Care', color: '#EC4899', iconName: 'HeartPulse' },
      Entertainment: { name: 'Entertainment', color: '#8B5CF6', iconName: 'Gamepad2' },
      Subscriptions: { name: 'Subscriptions', color: '#6366F1', iconName: 'CreditCard' },
    };

    // Generate new CategoryBudget objects from user allocations
    const newBudgets: CategoryBudget[] = CATEGORIES_LIST.map((key) => {
      const limit = categoryAllocations[key] ?? 0;
      const meta = CATEGORY_META[key] || { name: key, color: '#6366f1', iconName: 'Tag' };
      return {
        key,
        name: meta.name,
        iconName: meta.iconName,
        color: meta.color,
        accentColor: '',
        monthlyLimit: limit,
        aiSuggestedLimit: limit,
        spent: 0,
        isNeed: key === 'Transfers' || key === 'Food' || key === 'Utilities' || key === 'Health Care',
        isUserCustomized: true,
      };
    });

    const safeDaily = userDailySafeLimit !== undefined && userDailySafeLimit > 0 ? userDailySafeLimit : 100;

    // Save to local storage
    try {
      localStorage.setItem('wispend_phonepe_transactions', JSON.stringify(extractedTransactions));
      localStorage.setItem('wispend_phonepe_filename', activeFileName);
    } catch (_) {}

    onStatementLoaded(
      extractedTransactions,
      newBudgets,
      safeDaily,
      aiHabits,
      activeFileName,
      userMonthlyBudget,
      userSavingsLimit
    );

    setCurrentStep('report');
  };

  // Compute Review & Report Totals
  const totalDebits = extractedTransactions
    .filter((t) => t.type === 'DEBIT')
    .reduce((sum, t) => sum + (Number(t.amount) || 0), 0);

  const totalCredits = extractedTransactions
    .filter((t) => t.type === 'CREDIT')
    .reduce((sum, t) => sum + (Number(t.amount) || 0), 0);

  const totalReviewAmount = extractedTransactions.reduce((sum, t) => sum + (Number(t.amount) || 0), 0);

  const remainingMonthlyCap = Math.max(0, userMonthlyBudget - userSavingsLimit);
  const totalAllocatedSum = Object.values(categoryAllocations).reduce((a, b) => a + (Number(b) || 0), 0);
  const safeCapStatus = evaluateSafeCapStatus(categoryAllocations, remainingMonthlyCap);

  // Filtered in review
  const filteredReviewList = extractedTransactions.filter(
    (t) =>
      t.description.toLowerCase().includes(reviewSearch.toLowerCase()) ||
      t.category.toLowerCase().includes(reviewSearch.toLowerCase()) ||
      (t.upiRef && t.upiRef.toLowerCase().includes(reviewSearch.toLowerCase()))
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[92vh] flex flex-col bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl text-slate-100 overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 bg-slate-900/90 backdrop-blur">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">
                  PhonePe UPI Statement Import &amp; Budget Setup
                </h3>
                <p className="text-xs text-slate-400">
                  Read &rarr; Review &amp; AI Suggestions &rarr; Record &rarr; Monthly Report
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

          {/* Stepper Wizard Indicator */}
          <div className="grid grid-cols-4 gap-2 text-xs font-semibold">
            <div
              className={`p-2 rounded-xl text-center border transition-all ${
                currentStep === 'upload' || currentStep === 'reading'
                  ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                  : 'bg-slate-950/40 border-slate-800 text-slate-400'
              }`}
            >
              1. Upload &amp; Read
            </div>
            <div
              className={`p-2 rounded-xl text-center border transition-all ${
                currentStep === 'review'
                  ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                  : currentStep === 'report'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  : 'bg-slate-950/40 border-slate-800 text-slate-500'
              }`}
            >
              2. Review &amp; AI Budget
            </div>
            <div
              className={`p-2 rounded-xl text-center border transition-all ${
                currentStep === 'report'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                  : 'bg-slate-950/40 border-slate-800 text-slate-500'
              }`}
            >
              3. Record (Saved)
            </div>
            <div
              className={`p-2 rounded-xl text-center border transition-all ${
                currentStep === 'report'
                  ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                  : 'bg-slate-950/40 border-slate-800 text-slate-500'
              }`}
            >
              4. Monthly Report
            </div>
          </div>
        </div>

        {errorMsg && (
          <div className="mx-6 mt-4 flex items-center gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* STEP 1: UPLOAD */}
        {currentStep === 'upload' && (
          <div className="p-6 overflow-y-auto space-y-4 flex-1">
            <div className="flex p-1 bg-slate-950 rounded-xl border border-slate-800 text-xs font-medium">
              <button
                onClick={() => setActiveTab('upload')}
                className={`flex-1 py-2 rounded-lg transition-all ${
                  activeTab === 'upload' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                📄 Upload PDF / Statement
              </button>
              <button
                onClick={() => setActiveTab('paste')}
                className={`flex-1 py-2 rounded-lg transition-all ${
                  activeTab === 'paste' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                📋 Paste PhonePe Text
              </button>
              <button
                onClick={() => setActiveTab('sample')}
                className={`flex-1 py-2 rounded-lg transition-all ${
                  activeTab === 'sample' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                ⚡ Instant Verified Demo
              </button>
            </div>

            {activeTab === 'upload' ? (
              <div className="space-y-4 pt-2">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".pdf,.txt,.csv"
                  className="hidden"
                />

                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="p-10 border-2 border-dashed border-slate-700 hover:border-indigo-500/60 rounded-2xl bg-slate-950/40 hover:bg-slate-950/80 cursor-pointer flex flex-col items-center justify-center text-center transition-all group"
                >
                  <div className="w-14 h-14 rounded-2xl bg-slate-800 group-hover:bg-indigo-500/10 flex items-center justify-center text-slate-400 group-hover:text-indigo-400 mb-3 transition-colors">
                    <UploadCloud className="w-7 h-7" />
                  </div>
                  <p className="text-sm font-semibold text-slate-200 mb-1">
                    Select your PhonePe statement file (.pdf, .csv, .txt)
                  </p>
                  <p className="text-xs text-slate-500 max-w-sm">
                    Exported directly from PhonePe App &rarr; History &rarr; Download Statement
                  </p>
                </div>
              </div>
            ) : activeTab === 'paste' ? (
              <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs text-slate-400 font-medium">
                    Paste PhonePe statement transaction text:
                  </label>
                  <button
                    type="button"
                    onClick={() => setPasteContent(SAMPLE_PASTE_PHONEPE_TEXT)}
                    className="text-[11px] text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold"
                  >
                    <Copy className="w-3 h-3" />
                    <span>Fill PhonePe Format Template</span>
                  </button>
                </div>

                <textarea
                  value={pasteContent}
                  onChange={(e) => setPasteContent(e.target.value)}
                  placeholder="Paste PhonePe statement text..."
                  rows={8}
                  className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
                />

                <button
                  onClick={handlePasteSubmit}
                  className="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow"
                >
                  <span>Extract PhonePe Transactions</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <div className="space-y-4 pt-2">
                <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800 text-xs space-y-2">
                  <div className="font-semibold text-slate-200 flex items-center justify-between">
                    <span>Verified PhonePe UPI Dataset:</span>
                    <span className="text-[11px] text-emerald-400">30+ Verified Records</span>
                  </div>
                  <ul className="text-slate-400 space-y-1 list-disc list-inside">
                    <li>Swiggy, Zomato &amp; Blinkit food orders</li>
                    <li>Zerodha SIP &amp; Groww Mutual Funds</li>
                    <li>BESCOM Power, Airtel Fiber &amp; Gas bills</li>
                    <li>Salary Credit (₹1,18,000) &amp; Splits</li>
                  </ul>
                </div>

                <button
                  onClick={handleLoadSample}
                  className="w-full py-3.5 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white font-semibold text-sm flex items-center justify-center gap-2 shadow-lg"
                >
                  <span>Load Verified PhonePe Statement</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        )}

        {/* READING STATE */}
        {currentStep === 'reading' && (
          <div className="p-12 flex flex-col items-center justify-center text-center flex-1">
            <div className="relative mb-5">
              <div className="w-16 h-16 rounded-full border-4 border-indigo-500/20 border-t-indigo-500 animate-spin" />
              <div className="absolute inset-0 flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-indigo-400 animate-pulse" />
              </div>
            </div>
            <h4 className="text-base font-bold text-white mb-1">
              Reading PhonePe Statement Details
            </h4>
            <p className="text-xs text-indigo-300 animate-pulse mb-4">
              {processingStage}
            </p>
          </div>
        )}

        {/* STEP 2: REVIEW & FIX STAGE WITH MONTHLY BUDGET & AI SAVINGS PLANNER */}
        {currentStep === 'review' && (
          <div className="p-5 overflow-y-auto space-y-5 flex-1">
            {/* FEATURE 2 & 3 & 4: MONTHLY BUDGET INPUT + AI SAVINGS LIMIT + CATEGORY DIVISION */}
            <div className="p-4 rounded-2xl bg-slate-950 border border-indigo-500/40 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
                    <PiggyBank className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white">
                      Monthly Budget &amp; AI Savings Limit Setup
                    </h4>
                    <p className="text-[11px] text-slate-400">
                      Input your monthly budget &rarr; AI suggests savings limit &rarr; Divide remaining into categories (all editable)
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setShowBudgetDivider(!showBudgetDivider)}
                  className="text-xs text-indigo-400 hover:underline font-semibold"
                >
                  {showBudgetDivider ? 'Hide Setup' : 'Show Setup'}
                </button>
              </div>

              {showBudgetDivider && (
                <div className="space-y-4 pt-1">
                  {/* Inputs Row: Monthly Budget, AI Savings Limit, Monthly Safe Cap, and Editable Daily Safe Limit */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    {/* User Input Monthly Budget */}
                    <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                      <label className="text-[10px] font-bold uppercase text-slate-400 block mb-1">
                        1. Monthly Budget (INR ₹)
                      </label>
                      <div className="flex items-center gap-1 bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1">
                        <span className="text-slate-400 text-xs font-mono">₹</span>
                        <input
                          type="number"
                          step="1000"
                          min="1000"
                          value={userMonthlyBudget}
                          onChange={(e) => handleBudgetChange(Math.max(0, Number(e.target.value) || 0))}
                          className="w-full bg-transparent font-mono font-bold text-white text-sm focus:outline-none"
                        />
                      </div>
                      <span className="text-[10px] text-slate-500 mt-1 block">Total pool</span>
                    </div>

                    {/* AI Suggestion for Saving Limit (User editable) */}
                    <div className="p-3 rounded-xl bg-slate-900 border border-emerald-500/30">
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-[10px] font-bold uppercase text-emerald-400">
                          2. AI Savings Limit
                        </label>
                        <span className="text-[10px] text-emerald-300 font-mono">
                          Rec: ₹{aiSavingsSuggestion}
                        </span>
                      </div>
                      <div className="flex items-center gap-1 bg-slate-950 border border-emerald-500/40 rounded-lg px-2.5 py-1">
                        <span className="text-emerald-400 text-xs font-mono">₹</span>
                        <input
                          type="number"
                          step="500"
                          min="0"
                          max={userMonthlyBudget}
                          value={userSavingsLimit}
                          onChange={(e) => handleSavingsChange(Math.max(0, Number(e.target.value) || 0))}
                          className="w-full bg-transparent font-mono font-bold text-emerald-400 text-sm focus:outline-none"
                        />
                      </div>
                      <span className="text-[10px] text-slate-500 mt-1 block">Editable saving limit</span>
                    </div>

                    {/* Monthly Safe Spending Cap */}
                    <div className="p-3 rounded-xl bg-slate-900 border border-cyan-500/30 flex flex-col justify-between">
                      <div>
                        <span className="text-[10px] font-bold uppercase text-cyan-400 block mb-1">
                          3. Monthly Safe Cap
                        </span>
                        <div className="text-base font-bold font-mono text-cyan-300">
                          ₹{remainingMonthlyCap.toLocaleString('en-IN')}
                        </div>
                      </div>
                      <span className="text-[10px] text-slate-400">
                        Budget - Savings limit
                      </span>
                    </div>

                    {/* Daily Safe Limit (Dependent on Monthly Cap & User Editable) */}
                    <div className="p-3 rounded-xl bg-slate-900 border border-indigo-500/40 flex flex-col justify-between">
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-[10px] font-bold uppercase text-indigo-400">
                          4. 1-Day Safe Limit
                        </label>
                        <span className="text-[9px] text-indigo-300">
                          (Editable)
                        </span>
                      </div>
                      <div className="flex items-center gap-1 bg-slate-950 border border-indigo-500/50 rounded-lg px-2.5 py-1">
                        <span className="text-indigo-400 text-xs font-mono">₹</span>
                        <input
                          type="number"
                          step="100"
                          min="0"
                          value={userDailySafeLimit}
                          onChange={(e) => setUserDailySafeLimit(Math.max(0, Number(e.target.value) || 0))}
                          className="w-full bg-transparent font-mono font-bold text-indigo-300 text-sm focus:outline-none"
                        />
                      </div>
                      <span className="text-[10px] text-slate-400 mt-1 block">
                        Derived from safe cap
                      </span>
                    </div>
                  </div>

                  {/* AI Category Allocation Summary divided based on monthly safe spending cap */}
                  <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                      <div>
                        <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                          <span>AI Category Division Allocation (Sum equals Monthly Safe Cap ₹{remainingMonthlyCap.toLocaleString('en-IN')}):</span>
                        </span>
                        <span className="text-[11px] text-slate-400 block mt-0.5">
                          Every category is automatically divided from your safe spending cap and is user-editable.
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => divideBudgetAcrossCategories(userMonthlyBudget, userSavingsLimit)}
                        className="text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold whitespace-nowrap px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/20"
                      >
                        AI Auto-Balance to Safe Cap
                      </button>
                    </div>

                    {/* Total Amount under AI Budget UI */}
                    <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs">
                      <div className="flex items-center gap-2">
                        <span className="text-slate-400">Total Amount Allocated:</span>
                        <span className={`font-mono font-bold text-sm ${safeCapStatus.isCapExceeded ? 'text-rose-400' : 'text-emerald-400'}`}>
                          ₹{safeCapStatus.totalAllocated.toLocaleString('en-IN')}
                        </span>
                        <span className="text-slate-500">/</span>
                        <span className="text-slate-400">Monthly Safe Cap:</span>
                        <span className="font-mono font-bold text-cyan-300 text-sm">
                          ₹{remainingMonthlyCap.toLocaleString('en-IN')}
                        </span>
                      </div>
                      <div className="text-[11px] font-mono">
                        {safeCapStatus.isCapExceeded ? (
                          <span className="text-rose-400 font-bold">
                            +₹{safeCapStatus.difference.toLocaleString('en-IN')} Exceeded
                          </span>
                        ) : safeCapStatus.isExactMatch ? (
                          <span className="text-emerald-400 font-bold">
                            ✓ 100% Balanced to Cap
                          </span>
                        ) : (
                          <span className="text-amber-400">
                            ₹{(remainingMonthlyCap - safeCapStatus.totalAllocated).toLocaleString('en-IN')} Unallocated
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Safe Cap Limit Exceeded Banner */}
                    {safeCapStatus.isCapExceeded && (
                      <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/40 text-rose-300 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                          <div>
                            <span className="font-bold text-rose-200">Safe Cap Limit Exceeded!</span>
                            <span className="text-[11px] text-rose-300 block">
                              {safeCapStatus.anyIndividualExceeds
                                ? `An individual category (₹${safeCapStatus.maxIndividual.toLocaleString('en-IN')}) or category allocation sum (₹${safeCapStatus.totalAllocated.toLocaleString('en-IN')}) is greater than your monthly safe spending cap (₹${remainingMonthlyCap.toLocaleString('en-IN')}) by ₹${safeCapStatus.difference.toLocaleString('en-IN')}.`
                                : `The sum of individual category allocations (₹${safeCapStatus.totalAllocated.toLocaleString('en-IN')}) is greater than your monthly safe spending cap (₹${remainingMonthlyCap.toLocaleString('en-IN')}) by ₹${safeCapStatus.difference.toLocaleString('en-IN')}.`}
                            </span>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => divideBudgetAcrossCategories(userMonthlyBudget, userSavingsLimit)}
                          className="px-3 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 font-semibold text-xs whitespace-nowrap self-start sm:self-auto"
                        >
                          Re-balance to Safe Cap
                        </button>
                      </div>
                    )}

                    {safeCapStatus.isExactMatch && (
                      <div className="p-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                          <span>
                            <strong>AI Allocation Balanced:</strong> Sum of category division allocations (₹{safeCapStatus.totalAllocated.toLocaleString('en-IN')}) equals Monthly Safe Cap (₹{remainingMonthlyCap.toLocaleString('en-IN')}).
                          </span>
                        </div>
                        <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                          EXACT MATCH
                        </span>
                      </div>
                    )}

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                      {CATEGORIES_LIST.map((cat) => {
                        const isCatOver = (categoryAllocations[cat] || 0) > remainingMonthlyCap && remainingMonthlyCap > 0;
                        return (
                          <div
                            key={cat}
                            className={`p-2 rounded-lg bg-slate-950 border transition-colors ${
                              isCatOver ? 'border-rose-500/60 ring-1 ring-rose-500/30' : 'border-slate-800'
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] text-slate-400 truncate">{cat}</span>
                              {isCatOver && <span className="text-[9px] text-rose-400 font-bold">&gt; Safe Cap</span>}
                            </div>
                            <div className="flex items-center gap-1 mt-0.5">
                              <span className="text-[10px] text-slate-500 font-mono">₹</span>
                              <input
                                type="number"
                                step="100"
                                min="0"
                                value={categoryAllocations[cat] || 0}
                                onChange={(e) => handleCategoryAllocationChange(cat, Number(e.target.value) || 0)}
                                className={`w-full bg-transparent font-mono text-xs font-bold focus:outline-none ${
                                  isCatOver ? 'text-rose-300' : 'text-white'
                                }`}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Total Amount under Review Banner */}
            <div className="p-4 rounded-2xl bg-slate-900 border border-indigo-500/30 flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  <DollarSign className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    Total Amount under Review
                  </span>
                  <div className="text-xl sm:text-2xl font-extrabold font-mono text-white">
                    ₹{totalReviewAmount.toLocaleString('en-IN')}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 text-xs font-mono">
                <div className="px-3 py-1.5 rounded-xl bg-slate-950 border border-rose-500/30">
                  <span className="text-[10px] text-slate-400 block font-sans">Total Debits (Spent)</span>
                  <span className="text-rose-400 font-bold">₹{totalDebits.toLocaleString('en-IN')}</span>
                </div>
                <div className="px-3 py-1.5 rounded-xl bg-slate-950 border border-emerald-500/30">
                  <span className="text-[10px] text-slate-400 block font-sans">Total Credits (Income)</span>
                  <span className="text-emerald-400 font-bold">₹{totalCredits.toLocaleString('en-IN')}</span>
                </div>
                <div className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800">
                  <span className="text-[10px] text-slate-400 block font-sans">Transactions</span>
                  <span className="text-slate-200 font-bold">{extractedTransactions.length} Rows</span>
                </div>
              </div>
            </div>

            {/* REVIEW & FIX TRANSACTIONS TABLE */}
            <div className="space-y-2">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h4 className="text-xs font-bold text-white flex items-center gap-2">
                    <span>Extracted Transactions ({extractedTransactions.length})</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
                      {activeFileName}
                    </span>
                  </h4>
                  <p className="text-[11px] text-slate-400">
                    Category suggestion given by AI initially. You can change or fix any field below.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    placeholder="Search extracted rows..."
                    value={reviewSearch}
                    onChange={(e) => setReviewSearch(e.target.value)}
                    className="w-48 bg-slate-950 border border-slate-800 rounded-xl px-2.5 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none"
                  />
                  <button
                    onClick={handleAddManualRow}
                    className="px-2.5 py-1 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Row</span>
                  </button>
                </div>
              </div>

              {/* Editable Table */}
              <div className="border border-slate-800 rounded-2xl overflow-hidden bg-slate-950/60 max-h-72 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/90 sticky top-0 border-b border-slate-800 text-slate-400">
                    <tr>
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3">Description</th>
                      <th className="py-2.5 px-3">Category (AI Suggestion &amp; Input)</th>
                      <th className="py-2.5 px-3">Type</th>
                      <th className="py-2.5 px-3 text-right">Amount (₹)</th>
                      <th className="py-2.5 px-3 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {filteredReviewList.map((tx) => (
                      <tr key={tx.id} className="hover:bg-slate-900/50 transition-colors">
                        <td className="py-2 px-3 whitespace-nowrap">
                          <input
                            type="text"
                            value={tx.date}
                            onChange={(e) => handleUpdateTxField(tx.id, 'date', e.target.value)}
                            className="w-24 bg-transparent border-b border-transparent hover:border-slate-700 text-slate-300 text-xs focus:outline-none font-mono"
                          />
                        </td>

                        <td className="py-2 px-3">
                          <input
                            type="text"
                            value={tx.description}
                            onChange={(e) => handleUpdateTxField(tx.id, 'description', e.target.value)}
                            className="w-full bg-transparent border-b border-transparent hover:border-slate-700 text-slate-100 text-xs focus:outline-none font-sans"
                          />
                        </td>

                        {/* Category selection with initial AI suggestion badge */}
                        <td className="py-2 px-3">
                          <div className="flex items-center gap-1.5">
                            <select
                              value={tx.category}
                              onChange={(e) => handleUpdateTxField(tx.id, 'category', e.target.value as CategoryKey)}
                              className="bg-slate-900 border border-slate-700 rounded px-1.5 py-0.5 text-[11px] text-slate-200 focus:outline-none"
                            >
                              {CATEGORIES_LIST.map((c) => (
                                <option key={c} value={c}>
                                  {c}
                                </option>
                              ))}
                            </select>
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-400 font-sans border border-indigo-500/20 whitespace-nowrap hidden sm:inline">
                              AI: {tx.aiSuggestedCategory || tx.category}
                            </span>
                          </div>
                        </td>

                        <td className="py-2 px-3 whitespace-nowrap">
                          <button
                            type="button"
                            onClick={() => handleUpdateTxField(tx.id, 'type', tx.type === 'DEBIT' ? 'CREDIT' : 'DEBIT')}
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              tx.type === 'DEBIT' ? 'bg-rose-500/20 text-rose-400' : 'bg-emerald-500/20 text-emerald-400'
                            }`}
                          >
                            {tx.type}
                          </button>
                        </td>

                        <td className="py-2 px-3 text-right whitespace-nowrap">
                          <input
                            type="number"
                            value={tx.amount}
                            onChange={(e) => handleUpdateTxField(tx.id, 'amount', parseFloat(e.target.value) || 0)}
                            className={`w-20 bg-transparent text-right border-b border-transparent hover:border-slate-700 text-xs font-mono font-bold focus:outline-none ${
                              tx.type === 'DEBIT' ? 'text-slate-100' : 'text-emerald-400'
                            }`}
                          />
                        </td>

                        <td className="py-2 px-3 text-center">
                          <button
                            type="button"
                            onClick={() => handleDeleteExtractedTx(tx.id)}
                            className="text-slate-500 hover:text-rose-400 p-1 rounded hover:bg-slate-800 transition-colors"
                            title="Remove row"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  {/* Sticky Footer Total Amount under Review */}
                  <tfoot className="bg-slate-900 sticky bottom-0 border-t border-slate-700 text-xs font-mono">
                    <tr>
                      <td colSpan={4} className="py-2 px-3 font-sans font-bold text-slate-200">
                        Total Amount under Review:
                      </td>
                      <td className="py-2 px-3 text-right font-bold text-white text-sm">
                        ₹{totalReviewAmount.toLocaleString('en-IN')}
                      </td>
                      <td></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* Bottom Actions */}
            <div className="pt-2 flex items-center justify-between">
              <button
                type="button"
                onClick={handleReset}
                className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium flex items-center gap-1.5"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Upload Another File</span>
              </button>

              <button
                type="button"
                onClick={handleConfirmRecord}
                className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-emerald-600/20 active:scale-95 transition-all"
              >
                <Check className="w-4 h-4" />
                <span>Confirm &amp; Record Transactions &rarr;</span>
              </button>
            </div>
          </div>
        )}

        {/* STEP 4: REPORT STAGE */}
        {currentStep === 'report' && (
          <div className="p-6 overflow-y-auto space-y-5 flex-1">
            <div className="flex items-center gap-2.5 text-emerald-400">
              <CheckCircle2 className="w-6 h-6 flex-shrink-0" />
              <div>
                <h4 className="text-base font-bold text-white">
                  PhonePe UPI Statement Recorded &amp; Summarized
                </h4>
                <p className="text-xs text-slate-400">
                  Transactions committed to dashboard. Monthly safe zone limits and summaries computed below:
                </p>
              </div>
            </div>

            {/* Report Totals */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800">
                <span className="text-[11px] text-slate-400">Monthly Budget</span>
                <div className="text-lg font-bold font-mono text-white mt-1">
                  ₹{userMonthlyBudget.toLocaleString('en-IN')}
                </div>
              </div>
              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800">
                <span className="text-[11px] text-slate-400">Target Savings Limit</span>
                <div className="text-lg font-bold font-mono text-emerald-400 mt-1">
                  ₹{userSavingsLimit.toLocaleString('en-IN')}
                </div>
              </div>
              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800">
                <span className="text-[11px] text-slate-400">Monthly Safe Cap</span>
                <div className="text-lg font-bold font-mono text-cyan-400 mt-1">
                  ₹{remainingMonthlyCap.toLocaleString('en-IN')}
                </div>
              </div>
              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800">
                <span className="text-[11px] text-slate-400">1-Day Safe Zone</span>
                <div className="text-lg font-bold font-mono text-indigo-400 mt-1">
                  ₹{userDailySafeLimit.toLocaleString('en-IN')}/day
                </div>
              </div>
            </div>

            {/* Category Division Report */}
            <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-2">
              <span className="text-xs font-bold text-white">Category Allocation Summary:</span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                {CATEGORIES_LIST.map((c) => (
                  <div key={c} className="p-2 rounded-lg bg-slate-900 border border-slate-800 flex justify-between">
                    <span className="text-slate-400 text-[11px] truncate">{c}</span>
                    <strong className="text-slate-200 font-mono">₹{(categoryAllocations[c] || 0).toLocaleString('en-IN')}</strong>
                  </div>
                ))}
              </div>
            </div>

            {/* AI Insights */}
            {aiHabits && aiHabits.length > 0 && (
              <div className="p-4 rounded-2xl bg-indigo-950/30 border border-indigo-500/20 text-xs space-y-2">
                <span className="font-bold text-indigo-300 flex items-center gap-1.5">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  AI Spending Habit Insights
                </span>
                <ul className="space-y-1.5 text-slate-300 list-disc list-inside">
                  {aiHabits.map((h, i) => (
                    <li key={i}>{h}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                {extractedTransactions.length} PhonePe transactions saved &amp; ready
              </span>

              <button
                type="button"
                onClick={onClose}
                className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-md"
              >
                View on Financial Dashboard &rarr;
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
