import React, { useState } from 'react';
import { Bell, AlertTriangle, AlertCircle, Sparkles, Flame, Check, X, ShieldAlert, Smartphone } from 'lucide-react';
import { SmartAlert } from '../types';

interface SmartAlertsPanelProps {
  alerts: SmartAlert[];
  isOpen: boolean;
  onClose: () => void;
  onMarkAllRead: () => void;
  onSimulatePushBanner: (title: string, body: string) => void;
}

export const SmartAlertsPanel: React.FC<SmartAlertsPanelProps> = ({
  alerts,
  isOpen,
  onClose,
  onMarkAllRead,
  onSimulatePushBanner,
}) => {
  const [proximityThreshold, setProximityThreshold] = useState(80);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-end bg-slate-950/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-md h-full bg-slate-900 border-l border-slate-800 shadow-2xl p-6 flex flex-col justify-between text-slate-100 overflow-y-auto">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
                <Bell className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Smart Financial Alerts</h3>
                <p className="text-xs text-slate-400">
                  Over-budget triggers & daily safe limit notifications
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

          {/* Push Notification Simulator Card */}
          <div className="p-3.5 mb-5 rounded-2xl bg-indigo-950/40 border border-indigo-500/30 text-xs space-y-2.5">
            <div className="flex items-center justify-between text-indigo-300 font-semibold">
              <span className="flex items-center gap-1.5">
                <Smartphone className="w-4 h-4" />
                Push Notification System
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300">
                Simulated
              </span>
            </div>
            <p className="text-slate-400 text-[11px]">
              Receive alerts on mobile/desktop before hitting your 1-day safe limit.
            </p>

            <div className="flex items-center justify-between pt-1">
              <span className="text-slate-400 text-[11px]">Warning Trigger:</span>
              <div className="flex items-center gap-1">
                {[75, 80, 90].map((t) => (
                  <button
                    key={t}
                    onClick={() => setProximityThreshold(t)}
                    className={`px-2 py-0.5 rounded text-[11px] font-mono transition-colors ${
                      proximityThreshold === t
                        ? 'bg-indigo-600 text-white font-bold'
                        : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {t}%
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={() =>
                onSimulatePushBanner(
                  `⚠️ Daily Safe Limit Alert (${proximityThreshold}%)`,
                  `You've spent ₹960 of your ₹1,200 safe limit today. Keep remaining ₹240 safe to preserve your streak!`
                )
              }
              className="w-full py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors shadow"
            >
              <Bell className="w-3.5 h-3.5" />
              <span>Trigger Test Push Notification</span>
            </button>
          </div>

          {/* Mark All Read Button */}
          <div className="flex items-center justify-between mb-3 text-xs">
            <span className="text-slate-400 font-medium">Active Alert Feeds</span>
            <button
              onClick={onMarkAllRead}
              className="text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
            >
              <Check className="w-3 h-3" />
              <span>Mark all read</span>
            </button>
          </div>

          {/* Alert Feed Items */}
          <div className="space-y-3">
            {alerts.map((alert) => {
              const isDanger = alert.type === 'danger';
              const isWarning = alert.type === 'warning';
              const isProximity = alert.type === 'proximity';
              const isSafeZone = alert.type === 'safezone';

              return (
                <div
                  key={alert.id}
                  className={`p-3.5 rounded-2xl border transition-all ${
                    alert.read
                      ? 'bg-slate-950/40 border-slate-800/80 text-slate-400 opacity-75'
                      : 'bg-slate-950/90 border-slate-700/80 text-slate-200 shadow-md'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-xl flex-shrink-0 mt-0.5">
                      {isDanger ? (
                        <ShieldAlert className="w-4 h-4 text-rose-400" />
                      ) : isWarning ? (
                        <AlertTriangle className="w-4 h-4 text-amber-400" />
                      ) : isSafeZone || isProximity ? (
                        <ShieldAlert className="w-4 h-4 text-cyan-400" />
                      ) : (
                        <Sparkles className="w-4 h-4 text-indigo-400" />
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <h4 className="text-xs font-bold text-white truncate">
                          {alert.title}
                        </h4>
                        <span className="text-[10px] text-slate-500 whitespace-nowrap">
                          {alert.timestamp}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed mb-2">
                        {alert.message}
                      </p>

                      {alert.actionText && (
                        <span className="inline-block text-[11px] font-semibold text-indigo-400 hover:underline cursor-pointer">
                          {alert.actionText} &rarr;
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="pt-4 mt-6 border-t border-slate-800 text-center text-[11px] text-slate-500">
          Proactive notifications powered by FinStreak AI engine
        </div>
      </div>
    </div>
  );
};
