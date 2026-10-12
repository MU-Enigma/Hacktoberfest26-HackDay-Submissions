import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { PolicyContent } from "@/components/PolicyContent";
import { AuthShell } from "@/pages/Login";
import { useAuth } from "@/context/AuthContext";
import { api, errMsg } from "@/lib/api";

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [accept, setAccept] = useState(false);
  const [policy, setPolicy] = useState({ version: "1.0", allowed_domains: [] });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/policy").then((r) => setPolicy(r.data)).catch(() => {});
  }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.password.length < 8) return setError("Password must be at least 8 characters");
    if (!accept) return setError("You must accept the Responsible Use Policy to register");
    setBusy(true);
    try {
      await register({ ...form, accept_policy: true, policy_version: policy.version });
      toast.success("Account created. Welcome to Back2U!");
      nav(params.get("next") || "/");
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="Create your Back2U account" sub={policy.allowed_domains.length ? `Use your university email (${policy.allowed_domains.join(", ")}).` : "Use your university email address."}>
      <form onSubmit={submit} className="space-y-4" data-testid="register-form">
        <div className="space-y-1.5">
          <Label htmlFor="name">Full name</Label>
          <Input id="name" required value={form.name} onChange={set("name")} data-testid="register-name-input" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="reg-email">University email</Label>
          <Input id="reg-email" type="email" required value={form.email} onChange={set("email")} data-testid="register-email-input" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="reg-password">Password (min 8 characters)</Label>
          <Input id="reg-password" type="password" required value={form.password} onChange={set("password")} data-testid="register-password-input" />
        </div>
        <div>
          <Label>Back2U Responsible Use Policy</Label>
          <ScrollArea className="h-48 mt-1.5 rounded-xl border border-slate-200 bg-slate-50 p-4" data-testid="register-policy-box">
            <PolicyContent compact />
          </ScrollArea>
        </div>
        <label className="flex items-start gap-3 text-sm text-slate-700 cursor-pointer">
          <Checkbox checked={accept} onCheckedChange={(v) => setAccept(!!v)} data-testid="register-policy-checkbox" className="mt-0.5" />
          I have read and agree to the Back2U Responsible Use Policy.
        </label>
        {error && <p className="text-sm text-red-600" data-testid="register-error">{error}</p>}
        <Button type="submit" disabled={busy || !accept} className="w-full h-11 rounded-full bg-indigo-600 hover:bg-indigo-700" data-testid="register-submit-btn">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Create account"}
        </Button>
        <p className="text-xs text-slate-500">Email verification is not enabled in this demo; your email will show as unverified.</p>
      </form>
      <p className="text-sm text-slate-500 mt-4">Already registered? <Link to="/login" className="text-indigo-600 font-semibold" data-testid="register-login-link">Log in</Link></p>
    </AuthShell>
  );
}
