import React, { useEffect } from 'react';
import { Flame, Bell, X, ShieldAlert } from 'lucide-react';

interface PushNotificationToastProps {
  notification: {
    title: string;
    body: string;
    id: string;
  } | null;
  onDismiss: () => void;
}

export const PushNotificationToast: React.FC<PushNotificationToastProps> = ({
  notification,
  onDismiss,
}) => {
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => {
        onDismiss();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [notification, onDismiss]);

  if (!notification) return null;

  return (
    <div className="fixed top-4 inset-x-0 z-50 flex justify-center px-4 pointer-events-none">
      <div className="pointer-events-auto w-full max-w-md p-4 rounded-2xl bg-slate-900/95 border border-indigo-500/40 text-slate-100 shadow-2xl backdrop-blur-xl animate-in slide-in-from-top-4 duration-300 flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-orange-500 to-amber-500 flex items-center justify-center flex-shrink-0 shadow-md shadow-orange-500/20">
          <Flame className="w-5 h-5 text-white" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-0.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400">
              FinStreak Push Alert
            </span>
            <span className="text-[10px] text-slate-500">now</span>
          </div>
          <h4 className="text-xs font-bold text-white truncate">
            {notification.title}
          </h4>
          <p className="text-xs text-slate-300 mt-0.5 leading-snug">
            {notification.body}
          </p>
        </div>

        <button
          onClick={onDismiss}
          className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors flex-shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
