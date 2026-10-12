export type CategoryKey =
  | 'Food'
  | 'Entertainment'
  | 'Utilities'
  | 'Health Care'
  | 'Shopping'
  | 'Subscriptions'
  | 'Transfers'
  | 'Investments';

export type ChartType = 'bar' | 'line' | 'pie' | 'table';

export interface Transaction {
  id: string;
  date: string; // YYYY-MM-DD
  time?: string;
  description: string;
  merchant: string;
  type: 'DEBIT' | 'CREDIT';
  amount: number;
  category: CategoryKey;
  aiSuggestedCategory?: CategoryKey; // Category suggestion given by AI initially
  upiRef?: string;
  note?: string;
  includeInSafeZone?: boolean; // User can de-select from 1-day safe zone
  source?: string; // 'user_phonepe_statement' | 'sample'
}

export interface CategoryBudget {
  key: CategoryKey;
  name: string;
  iconName: string;
  color: string;
  accentColor: string;
  monthlyLimit: number;
  aiSuggestedLimit: number;
  spent: number;
  isNeed: boolean;
  rationale?: string;
  isUserCustomized?: boolean;
}

export interface DaySpending {
  date: string; // YYYY-MM-DD
  dayLabel: string;
  spent: number;
  limit: number;
  status: 'safe' | 'over';
}

export interface SafeZoneConfig {
  // 1-Day Safe Zone UI data
  dailySafeLimit: number;
  todaySpent: number;

  // Monthly Safe Zone UI data
  monthlyBudget: number; // User inputted monthly budget
  savingsLimit: number; // AI suggested & user editable saving limit
  aiSuggestedSavingsLimit: number; // Original AI suggestion
  monthlySafeLimit: number; // Monthly safe spending limit = monthlyBudget - savingsLimit
  monthSpent: number;

  // Historical velocity data
  history: DaySpending[];
}

export interface SavingsGoal {
  id: string;
  name: string;
  targetAmount: number;
  currentAmount: number;
  targetDate: string;
  category: string;
  icon: string;
  color: string;
}

export interface SmartAlert {
  id: string;
  type: 'danger' | 'warning' | 'safezone' | 'insight' | 'proximity';
  title: string;
  message: string;
  category?: CategoryKey;
  timestamp: string;
  read: boolean;
  actionText?: string;
}

export interface BiometricConfig {
  isLocked: boolean;
  biometricEnabled: boolean;
  stealthMode: boolean;
  autoLockMinutes: number;
  savedPin: string;
}
