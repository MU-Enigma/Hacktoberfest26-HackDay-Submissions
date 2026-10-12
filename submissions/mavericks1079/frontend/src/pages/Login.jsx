import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Loader2, LogIn, UserRound } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/context/AuthContext";
import { errMsg } from "@/lib/api";

const DEMOS = [["alice@campus.edu", "Alice (demo student)"], ["bob@campus.edu", "Bob (demo student)"], ["carol@campus.edu", "Carol (demo student)"]];

export const AuthShell = ({ title, sub, children }) => (
  <div className="min-h-[calc(100vh-4rem)] grid-bg flex items-center justify-center px-4 py-12">
    <div className="w-full max-w-md card-surface p-8 fade-up">
      <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
      <p className="text-sm text-slate-500 mt-1 mb-6">{sub}</p>
      {children}
    </div>
  </div>
);

export default function Login() {
  const { login, demoLogin } = useAuth();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const next = params.get("next") || "/";

  const run = async (fn) => {
    setBusy(true);
    setError("");
    try {
      const u = await fn();
      toast.success(`Welcome back, ${u.name}`);
      nav(next);
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Log in to Back2U" sub="Use your university account to report and claim items.">
      <form onSubmit={(e) => { e.preventDefault(); run(() => login(email, password)); }} className="space-y-4" data-testid="login-form">
        <div className="space-y-1.5">
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="login-email-input" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Password</Label>
          <Input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} data-testid="login-password-input" />
        </div>
        {error && <p className="text-sm text-red-600" data-testid="login-error">{error}</p>}
        <Button type="submit" disabled={busy} className="w-full h-11 rounded-full bg-indigo-600 hover:bg-indigo-700" data-testid="login-submit-btn">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <><LogIn className="h-4 w-4 mr-2" />Log in</>}
        </Button>
      </form>
      <p className="text-sm text-slate-500 mt-4">No account? <Link to={`/register?next=${encodeURIComponent(next)}`} className="text-indigo-600 font-semibold" data-testid="login-register-link">Sign up</Link></p>
      <div className="mt-6 pt-6 border-t border-slate-200">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Hackathon demo mode</p>
        <p className="text-xs text-slate-500 mb-3">Sign in instantly as a sample student account (no admin rights, email not verified).</p>
        <div className="flex flex-col gap-2">
          {DEMOS.map(([em, label]) => (
            <Button key={em} variant="outline" disabled={busy} onClick={() => run(() => demoLogin(em))} className="justify-start rounded-full" data-testid={`demo-login-${em.split("@")[0]}`}>
              <UserRound className="h-4 w-4 mr-2" />{label}
            </Button>
          ))}
        </div>
      </div>
    </AuthShell>
  );
}
