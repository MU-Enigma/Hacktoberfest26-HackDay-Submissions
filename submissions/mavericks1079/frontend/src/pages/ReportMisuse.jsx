import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Loader2, ShieldAlert, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, errMsg } from "@/lib/api";
import { ABUSE_REASONS } from "@/lib/constants";

export default function ReportMisuse() {
  const [params] = useSearchParams();
  const [form, setForm] = useState({ target_type: params.get("type") || "other", target_id: params.get("id") || "", reason: "", details: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.reason) return setError("Choose a reason");
    setBusy(true);
    setError("");
    try {
      const { data } = await api.post("/moderation/reports", { ...form, target_id: form.target_id || null });
      setDone(data.reference);
    } catch (err) {
      setError(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-12" data-testid="report-misuse-page">
      <span className="overline-label">Trust & safety</span>
      <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 mt-1 flex items-center gap-2"><ShieldAlert className="h-7 w-7 text-red-500" />Report misuse</h1>
      <p className="text-slate-600 mt-2">For fake reports, false ownership claims, ownership disputes or harassment. Reports are reviewed by administrators only. Never include passwords or authentication codes.</p>
      {done ? (
        <div className="card-surface p-8 mt-6 text-center" data-testid="report-misuse-success">
          <CheckCircle2 className="h-10 w-10 text-emerald-600 mx-auto" />
          <p className="mt-3 font-semibold text-slate-900">Report received</p>
          <p className="text-sm text-slate-500">Reference number: <span className="font-mono font-bold">{done}</span></p>
        </div>
      ) : (
        <form onSubmit={submit} className="card-surface p-6 mt-6 space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>What are you reporting?</Label>
              <Select value={form.target_type} onValueChange={(v) => setForm({ ...form, target_type: v })}>
                <SelectTrigger data-testid="misuse-type-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[["item", "An item report"], ["claim", "A claim"], ["user", "A user"], ["other", "Other / dispute"]].map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="misuse-id">Related item or report ID (optional)</Label>
              <Input id="misuse-id" value={form.target_id} onChange={(e) => setForm({ ...form, target_id: e.target.value })} data-testid="misuse-target-input" />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Reason</Label>
            <Select value={form.reason} onValueChange={(v) => setForm({ ...form, reason: v })}>
              <SelectTrigger data-testid="misuse-reason-select"><SelectValue placeholder="Select a reason" /></SelectTrigger>
              <SelectContent>{ABUSE_REASONS.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="misuse-details">Details</Label>
            <Textarea id="misuse-details" rows={5} value={form.details} onChange={(e) => setForm({ ...form, details: e.target.value })} data-testid="misuse-details-input" />
          </div>
          {error && <p className="text-sm text-red-600" data-testid="misuse-error">{error}</p>}
          <Button type="submit" disabled={busy} className="bg-red-600 hover:bg-red-700" data-testid="misuse-submit-btn">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Submit report"}</Button>
        </form>
      )}
    </div>
  );
}
