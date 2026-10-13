import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ShieldCheck, MailWarning, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { PhotoUpload } from "@/components/report/PhotoUpload";
import { useAuth } from "@/context/AuthContext";
import { api, errMsg, fileUrl, fmtDate } from "@/lib/api";

function AppealSection({ user }) {
  const [appeals, setAppeals] = useState([]);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const load = () => api.get("/appeals/mine").then((r) => setAppeals(r.data));
  useEffect(() => {
    load();
  }, []);
  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/appeals", { message: msg });
      toast.success("Appeal submitted for administrator review");
      setMsg("");
      load();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="card-surface p-6 space-y-3" data-testid="appeal-section">
      <h2 className="font-bold text-slate-900">Moderation appeals</h2>
      <p className="text-sm text-slate-500">If you disagree with a moderation decision, explain why. A human administrator will review it.</p>
      {user.status !== "active" && <p className="text-sm text-red-600 font-semibold">Account status: {user.status}{user.suspended_until ? ` until ${fmtDate(user.suspended_until)}` : ""}</p>}
      <Textarea value={msg} onChange={(e) => setMsg(e.target.value)} rows={3} placeholder="Explain your appeal (10+ characters)" data-testid="appeal-message-input" />
      <Button onClick={submit} disabled={busy || msg.length < 10} variant="outline" data-testid="appeal-submit-btn">Submit appeal</Button>
      {appeals.map((a) => (
        <div key={a.id} className="text-sm rounded-lg bg-slate-50 p-3" data-testid={`appeal-${a.id}`}>
          <span className="font-semibold">{a.status}</span> · {fmtDate(a.created_at)}<div className="text-slate-600">{a.message}</div>{a.note && <div className="text-slate-500 mt-1">Admin: {a.note}</div>}
        </div>
      ))}
    </section>
  );
}

export default function Profile() {
  const { user, setUser } = useAuth();
  const [name, setName] = useState(user.name);
  const [avatar, setAvatar] = useState(user.avatar_path);
  const [prefs, setPrefs] = useState(user.notification_prefs);
  const [busy, setBusy] = useState(false);

  const save = async (patch) => {
    setBusy(true);
    try {
      const { data } = await api.patch("/profile", patch);
      setUser(data);
      toast.success("Profile updated");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10 space-y-6" data-testid="profile-page">
      <div><span className="overline-label">Account</span><h1 className="text-3xl font-extrabold tracking-tight text-slate-900 mt-1">Profile</h1></div>
      <section className="card-surface p-6 space-y-4">
        <div className="flex items-center gap-4">
          {avatar ? <img src={fileUrl(avatar)} alt="" className="h-16 w-16 rounded-full object-cover" /> : <span className="h-16 w-16 rounded-full bg-indigo-100 text-indigo-700 grid place-items-center text-xl font-bold">{user.name[0]}</span>}
          <div>
            <div className="font-semibold text-slate-900" data-testid="profile-email">{user.email}</div>
            <div className="text-xs flex items-center gap-1 text-amber-700" data-testid="profile-email-verified"><MailWarning className="h-3.5 w-3.5" />{user.email_verified ? "Email verified" : "Email not verified (verification not enabled in demo)"}</div>
            <div className="text-xs text-slate-500">Role: {user.role} · Status: <span data-testid="profile-status">{user.status}</span>{user.is_demo ? " · Demo account" : ""}</div>
          </div>
        </div>
        <div className="space-y-1.5"><Label htmlFor="p-name">Name</Label><Input id="p-name" value={name} onChange={(e) => setName(e.target.value)} data-testid="profile-name-input" /></div>
        <div className="space-y-1.5"><Label>Profile image (optional)</Label><PhotoUpload paths={avatar ? [avatar] : []} max={1} onChange={(p) => setAvatar(p[0] || "")} testId="profile-avatar" /></div>
        <Button onClick={() => save({ name, avatar_path: avatar || "" })} disabled={busy} className="bg-indigo-600 hover:bg-indigo-700" data-testid="profile-save-btn">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save profile"}</Button>
      </section>
      <section className="card-surface p-6 space-y-3" data-testid="notification-prefs">
        <h2 className="font-bold text-slate-900">Notification controls</h2>
        {[["matches", "Potential match alerts"], ["claims", "Claim updates"], ["watchlist", "Watchlist alerts"]].map(([k, l]) => (
          <label key={k} className="flex items-center justify-between text-sm">
            {l}
            <Switch checked={prefs[k]} onCheckedChange={(v) => { const p = { ...prefs, [k]: v }; setPrefs(p); save({ notification_prefs: p }); }} data-testid={`pref-${k}`} />
          </label>
        ))}
      </section>
      <section className="card-surface p-6 text-sm text-slate-600 flex gap-3" data-testid="policy-acceptance-info">
        <ShieldCheck className="h-5 w-5 text-emerald-600 shrink-0" />
        <div>Responsible Use Policy v{user.policy_version} accepted {fmtDate(user.policy_accepted_at)}. <Link to="/policy" className="text-indigo-600 font-semibold">Read the policy</Link></div>
      </section>
      <AppealSection user={user} />
    </div>
  );
}
