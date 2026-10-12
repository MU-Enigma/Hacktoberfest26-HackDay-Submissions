import React from 'react';
import { Shield, Lock, Eye, EyeOff, Bell, Moon, Sun, UploadCloud, Sliders, ShieldCheck } from 'lucide-react';
import { SafeZoneConfig } from '../types';
import { WispendLogo } from './WispendLogo';

interface HeaderNavProps {
  isDarkMode: boolean;
  onToggleTheme: () => void;
  stealthMode: boolean;
  onToggleStealth: () => void;
  onLockApp: () => void;
  onOpenUpload: () => void;
  onOpenBudgets: () => void;
  onOpenSafeZone: () => void;
  onOpenAlerts: () => void;
  unreadAlertCount: number;
  safeZone: SafeZoneConfig;
}

export const HeaderNav: React.FC<HeaderNavProps> = ({
  isDarkMode,
  onToggleTheme,
  stealthMode,
  onToggleStealth,
  onLockApp,
  onOpenUpload,
  onOpenBudgets,
  onOpenSafeZone,
  onOpenAlerts,
  unreadAlertCount,
  safeZone,
}) => {
  const isDailyOver = safeZone.todaySpent > safeZone.dailySafeLimit;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        {/* Left: Brand Logo & Status */}
        <WispendLogo size="md" />

        {/* Center: 1-Day Safe Zone Pill (Replaced Streak System) */}
        <div
          onClick={onOpenSafeZone}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-2xl border cursor-pointer transition-colors shadow-sm ${
            isDailyOver
              ? 'bg-rose-500/10 border-rose-500/30 text-rose-300'
              : 'bg-slate-900 border-slate-800 hover:border-cyan-500/40 text-slate-200'
          }`}
          title="Click to manage 1-Day Safe Zone Inclusions"
        >
          <Shield className={`w-4 h-4 ${isDailyOver ? 'text-rose-400' : 'text-cyan-400'}`} />
          <span className="text-xs font-bold font-mono">
            {safeZone.dailySafeLimit > 0
              ? `₹${safeZone.todaySpent} / ₹${safeZone.dailySafeLimit}`
              : '₹0 / ₹0'}
          </span>
          <span className="text-[10px] text-slate-400 hidden md:inline">
            {safeZone.dailySafeLimit > 0 ? '1-Day Safe Zone' : 'Safe Zone (Awaiting Import)'}
          </span>
        </div>

        {/* Right Action Icons */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Statement Import */}
          <button
            onClick={onOpenUpload}
            className="px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-indigo-600/20 active:scale-95 transition-all"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Import Statement</span>
          </button>

          {/* Manage Budgets */}
          <button
            onClick={onOpenBudgets}
            className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-colors"
            title="Custom Budgets & AI Savings Target"
          >
            <Sliders className="w-4 h-4" />
          </button>

          {/* Stealth Mode Toggle */}
          <button
            onClick={onToggleStealth}
            className={`p-2 rounded-xl border transition-colors ${
              stealthMode
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                : 'bg-slate-900 hover:bg-slate-800 border-slate-800 text-slate-400 hover:text-white'
            }`}
            title={stealthMode ? 'Disable Stealth Mode (Showing Balances)' : 'Enable Stealth Mode (Mask Sensitive Amounts)'}
          >
            {stealthMode ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>

          {/* Dark / Light Mode Toggle */}
          <button
            onClick={onToggleTheme}
            className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-400 hover:text-white transition-colors"
            title={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          >
            {isDarkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-400" />}
          </button>

          {/* Smart Alerts with Unread Badge */}
          <button
            onClick={onOpenAlerts}
            className="relative p-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 hover:text-white transition-colors"
            title="Smart Alerts"
          >
            <Bell className="w-4 h-4" />
            {unreadAlertCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-rose-500 text-[10px] font-bold text-white flex items-center justify-center shadow">
                {unreadAlertCount}
              </span>
            )}
          </button>

          {/* Biometric Screen Lock */}
          <button
            onClick={onLockApp}
            className="p-2 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 transition-colors"
            title="Lock Vault with Biometrics"
          >
            <Lock className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
