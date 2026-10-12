import React, { useState, useEffect } from 'react';
import { Fingerprint, Scan, ShieldCheck, KeyRound, Lock, Eye, EyeOff, AlertCircle } from 'lucide-react';

interface BiometricLockModalProps {
  isOpen: boolean;
  onUnlock: () => void;
  savedPin: string;
  stealthMode: boolean;
  onToggleStealth: () => void;
}

export const BiometricLockModal: React.FC<BiometricLockModalProps> = ({
  isOpen,
  onUnlock,
  savedPin,
  stealthMode,
  onToggleStealth,
}) => {
  const [authMode, setAuthMode] = useState<'biometric' | 'pin'>('biometric');
  const [pinInput, setPinInput] = useState('');
  const [pinError, setPinError] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [scanSuccess, setScanSuccess] = useState(false);
  const [biometricType, setBiometricType] = useState<'fingerprint' | 'face'>('fingerprint');

  useEffect(() => {
    if (isOpen) {
      setPinInput('');
      setPinError(false);
      setScanSuccess(false);
      // Auto-trigger simulated scan on open if in biometric mode
      setIsScanning(true);
      const timer = setTimeout(() => {
        setIsScanning(false);
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSimulateBiometric = () => {
    setIsScanning(true);
    setPinError(false);
    setTimeout(() => {
      setIsScanning(false);
      setScanSuccess(true);
      setTimeout(() => {
        onUnlock();
      }, 600);
    }, 1000);
  };

  const handlePinDigit = (digit: string) => {
    if (pinInput.length < 4) {
      const nextPin = pinInput + digit;
      setPinInput(nextPin);
      if (nextPin.length === 4) {
        if (nextPin === savedPin) {
          setScanSuccess(true);
          setTimeout(() => {
            onUnlock();
          }, 400);
        } else {
          setPinError(true);
          setTimeout(() => {
            setPinInput('');
            setPinError(false);
          }, 900);
        }
      }
    }
  };

  const handlePinDelete = () => {
    setPinInput((prev) => prev.slice(0, -1));
    setPinError(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-xl animate-in fade-in duration-200">
      <div className="relative w-full max-w-sm p-6 overflow-hidden bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl text-slate-100 text-center">
        {/* Glow backdrop */}
        <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-48 h-48 bg-emerald-500/20 rounded-full blur-3xl pointer-events-none" />

        {/* Lock header */}
        <div className="inline-flex items-center justify-center w-12 h-12 mb-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
          <Lock className="w-6 h-6" />
        </div>

        <h2 className="text-xl font-bold tracking-tight text-white mb-1">
          Wispend Security Lock
        </h2>
        <p className="text-xs text-slate-400 mb-6">
          Encrypted financial statement & budget vault
        </p>

        {authMode === 'biometric' ? (
          <div className="flex flex-col items-center">
            {/* Interactive Biometric Scanner Area */}
            <div className="relative my-4">
              <button
                type="button"
                onClick={handleSimulateBiometric}
                disabled={isScanning || scanSuccess}
                className={`relative group w-32 h-32 rounded-3xl flex items-center justify-center transition-all duration-300 border ${
                  scanSuccess
                    ? 'bg-emerald-500/20 border-emerald-400 text-emerald-400 ring-4 ring-emerald-500/30'
                    : isScanning
                    ? 'bg-slate-800/80 border-cyan-400 text-cyan-400 ring-4 ring-cyan-500/30'
                    : 'bg-slate-800/50 hover:bg-slate-800 border-slate-700 text-slate-300 hover:text-emerald-400 hover:border-emerald-500/50'
                }`}
                title="Tap to verify biometric credentials"
              >
                {/* Scan beam */}
                {isScanning && (
                  <div className="absolute inset-x-2 h-1 bg-cyan-400 shadow-[0_0_12px_#22d3ee] animate-scan-beam pointer-events-none" />
                )}

                {scanSuccess ? (
                  <ShieldCheck className="w-16 h-16 animate-bounce text-emerald-400" />
                ) : biometricType === 'fingerprint' ? (
                  <Fingerprint className={`w-16 h-16 transition-transform duration-300 ${isScanning ? 'scale-110' : 'group-hover:scale-105'}`} />
                ) : (
                  <Scan className={`w-16 h-16 transition-transform duration-300 ${isScanning ? 'scale-110' : 'group-hover:scale-105'}`} />
                )}
              </button>

              {/* Status Indicator */}
              <div className="mt-3 text-xs font-medium">
                {scanSuccess ? (
                  <span className="text-emerald-400">Verified. Unlocking vault...</span>
                ) : isScanning ? (
                  <span className="text-cyan-400 animate-pulse">Scanning biometric identity...</span>
                ) : (
                  <span className="text-slate-400">Touch sensor to authenticate</span>
                )}
              </div>
            </div>

            {/* Switch to Face/Touch and PIN */}
            <div className="flex items-center gap-2 mt-4">
              <button
                onClick={() => setBiometricType(biometricType === 'fingerprint' ? 'face' : 'fingerprint')}
                className="text-xs text-slate-400 hover:text-slate-200 transition-colors py-1 px-2.5 rounded-lg border border-slate-800 hover:border-slate-700"
              >
                Switch to {biometricType === 'fingerprint' ? 'Face ID' : 'Touch ID'}
              </button>
              <button
                onClick={() => setAuthMode('pin')}
                className="text-xs text-emerald-400 hover:text-emerald-300 transition-colors py-1 px-2.5 rounded-lg border border-slate-800 hover:border-slate-700"
              >
                Use 4-digit PIN
              </button>
            </div>
          </div>
        ) : (
          /* PIN Input Mode */
          <div className="flex flex-col items-center">
            {/* PIN Dots */}
            <div className="flex items-center justify-center gap-3 mb-6">
              {[0, 1, 2, 3].map((i) => (
                <div
                  key={i}
                  className={`w-3.5 h-3.5 rounded-full transition-all duration-200 ${
                    pinError
                      ? 'bg-rose-500 ring-2 ring-rose-500/40 animate-shake'
                      : i < pinInput.length
                      ? 'bg-emerald-400 ring-2 ring-emerald-500/30 scale-110'
                      : 'bg-slate-700'
                  }`}
                />
              ))}
            </div>

            {pinError && (
              <div className="flex items-center gap-1.5 text-xs text-rose-400 mb-3 animate-in fade-in">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Incorrect PIN. Try 1234 (default demo PIN).</span>
              </div>
            )}

            {/* Numeric Keypad */}
            <div className="grid grid-cols-3 gap-2.5 w-full max-w-[240px]">
              {['1', '2', '3', '4', '5', '6', '7', '8', '9'].map((digit) => (
                <button
                  key={digit}
                  onClick={() => handlePinDigit(digit)}
                  className="h-12 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-lg font-semibold text-slate-200 active:scale-95 transition-all"
                >
                  {digit}
                </button>
              ))}
              <button
                onClick={() => setAuthMode('biometric')}
                className="h-12 rounded-xl bg-slate-800/40 hover:bg-slate-800 text-slate-400 flex items-center justify-center transition-all"
                title="Switch back to Biometrics"
              >
                <Fingerprint className="w-5 h-5 text-emerald-400" />
              </button>
              <button
                onClick={() => handlePinDigit('0')}
                className="h-12 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-lg font-semibold text-slate-200 active:scale-95 transition-all"
              >
                0
              </button>
              <button
                onClick={handlePinDelete}
                className="h-12 rounded-xl bg-slate-800/40 hover:bg-slate-800 text-slate-400 text-xs font-semibold uppercase flex items-center justify-center transition-all active:scale-95"
              >
                Del
              </button>
            </div>

            <p className="text-[11px] text-slate-500 mt-4">
              Default demo PIN is <span className="font-mono text-emerald-400">1234</span>
            </p>
          </div>
        )}

        {/* Footer controls: Stealth Mode Toggle */}
        <div className="pt-6 mt-6 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <button
              onClick={onToggleStealth}
              className="flex items-center gap-1.5 hover:text-slate-200 transition-colors"
            >
              {stealthMode ? (
                <>
                  <EyeOff className="w-3.5 h-3.5 text-amber-400" />
                  <span>Stealth Mode Active</span>
                </>
              ) : (
                <>
                  <Eye className="w-3.5 h-3.5 text-slate-400" />
                  <span>Mask Balances</span>
                </>
              )}
            </button>
          </div>
          <span className="text-[11px] text-slate-500">AES-256 Vault</span>
        </div>
      </div>
    </div>
  );
};
