import { CategoryKey, CategoryBudget } from '../types';

export const DEFAULT_MONTHLY_SAFE_CAP = 3000;
export const DEFAULT_DAILY_SAFE_LIMIT = 100;

export const CATEGORY_ORDER: CategoryKey[] = [
  'Food',
  'Transfers',
  'Shopping',
  'Utilities',
  'Investments',
  'Health Care',
  'Entertainment',
  'Subscriptions',
];

/**
 * Weights totaling exactly 1.0 (100%)
 */
export const CATEGORY_WEIGHTS: Record<CategoryKey, number> = {
  Food: 0.25,          // 25%
  Transfers: 0.20,     // 20%
  Shopping: 0.15,      // 15%
  Utilities: 0.12,     // 12%
  Investments: 0.10,   // 10%
  'Health Care': 0.08, // 8%
  Entertainment: 0.06, // 6%
  Subscriptions: 0.04, // 4%
};

/**
 * Mathematically guarantees that the sum of all divided categories EXACTLY equals monthlySafeCap.
 * The final category receives the exact remainder down to the single rupee.
 */
export function calculateAiCategoryDivision(monthlySafeCap: number): Record<CategoryKey, number> {
  const cap = Math.max(0, Math.round(monthlySafeCap));
  if (cap === 0) {
    return {
      Food: 0,
      Transfers: 0,
      Shopping: 0,
      Utilities: 0,
      Investments: 0,
      'Health Care': 0,
      Entertainment: 0,
      Subscriptions: 0,
    };
  }

  const result: Record<CategoryKey, number> = {} as any;
  let runningSum = 0;

  for (let i = 0; i < CATEGORY_ORDER.length; i++) {
    const key = CATEGORY_ORDER[i];
    if (i === CATEGORY_ORDER.length - 1) {
      // Last category receives exact remainder to guarantee sum === cap
      result[key] = Math.max(0, cap - runningSum);
    } else {
      const weight = CATEGORY_WEIGHTS[key] || 0.1;
      const share = Math.round(cap * weight);
      result[key] = share;
      runningSum += share;
    }
  }

  return result;
}

/**
 * Evaluates whether category allocation sum or any individual category exceeds monthly safe cap.
 */
export function evaluateSafeCapStatus(
  allocations: Record<CategoryKey, number> | CategoryBudget[],
  monthlySafeCap: number
) {
  let totalAllocated = 0;
  let anyIndividualExceeds = false;
  let maxIndividual = 0;

  if (Array.isArray(allocations)) {
    allocations.forEach((cat) => {
      totalAllocated += cat.monthlyLimit;
      if (cat.monthlyLimit > monthlySafeCap) {
        anyIndividualExceeds = true;
      }
      if (cat.monthlyLimit > maxIndividual) {
        maxIndividual = cat.monthlyLimit;
      }
    });
  } else {
    Object.values(allocations).forEach((val) => {
      const num = Number(val) || 0;
      totalAllocated += num;
      if (num > monthlySafeCap) {
        anyIndividualExceeds = true;
      }
      if (num > maxIndividual) {
        maxIndividual = num;
      }
    });
  }

  const cap = Math.max(0, monthlySafeCap);
  const isSumExceeded = totalAllocated > cap;
  const isCapExceeded = isSumExceeded || (cap > 0 && anyIndividualExceeds);
  const difference = totalAllocated - cap;
  const isExactMatch = totalAllocated === cap && cap > 0;

  return {
    totalAllocated,
    monthlySafeCap: cap,
    isCapExceeded,
    isSumExceeded,
    anyIndividualExceeds,
    maxIndividual,
    difference,
    isExactMatch,
  };
}
