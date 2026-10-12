import { useCallback, useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import { QrCode, CheckCircle2, Circle, MapPin, ShieldCheck, Loader2, RefreshCw, XCircle } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ProtectedRoute";
import { ItemThumb } from "@/components/ItemCard";
import { QrScanner } from "@/components/handover/QrScanner";
import { api, errMsg, fmtDate } from "@/lib/api";

const Step = ({ done, label, testId }) => (
  <div className="flex items-center gap-2 text-sm" data-testid={testId}>
    {done ? <CheckCircle2 className="h-5 w-5 text-emerald-600" /> : <Circle className="h-5 w-5 text-slate-300" />}
    <span className={done ? "text-slate-900 font-medium" : "text-slate-500"}>{label}</span>
  </div>
);

function FinderPanel({ h, reload }) {
  const [tok, setTok] = useState(null);
  const [busy, setBusy] = useState(false);
  const issue = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/handovers/${h.id}/token`);
      setTok(data);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  const confirm = async () => {
    try {
      const { data } = await api.post(`/handovers/${h.id}/finder-confirm`);
      toast.success(data.status === "completed" ? "Handover complete. Receipt issued." : "Confirmed. Waiting for the owner to scan.");
      reload();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <div className="space-y-5">
      {!h.claimant_confirmed_at && (
        <div className="rounded-xl border border-slate-200 p-5 text-center" data-testid="finder-qr-panel">
          {tok ? (
            <>
              <QRCodeSVG value={`${window.location.origin}/handover/scan?t=${tok.token}`} size={200} className="mx-auto" data-testid="handover-qr" />
              <div className="mt-3 text-xs text-slate-500">Or share this one-time code in person</div>
              <div className="font-mono text-3xl font-bold tracking-[0.3em] text-slate-900" data-testid="handover-code">{tok.code}</div>
              <div className="text-xs text-slate-500 mt-1">Single use · expires {fmtDate(tok.expires_at)} · generating a new code invalidates this one</div>
            </>
          ) : <p className="text-sm text-slate-600">Generate the QR only when you meet the owner. It contains no personal data.</p>}
          <Button onClick={issue} disabled={busy} className="mt-4 bg-indigo-600 hover:bg-indigo-700" data-testid="generate-qr-btn">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <>{tok ? <RefreshCw className="h-4 w-4 mr-2" /> : <QrCode className="h-4 w-4 mr-2" />}{tok ? "Regenerate code" : "Generate handover QR"}</>}
          </Button>
        </div>
      )}
      {!h.finder_confirmed_at && (
        <Button onClick={confirm} className="w-full h-12 rounded-full bg-emerald-600 hover:bg-emerald-700 font-bold" data-testid="finder-confirm-btn">I have physically handed over the item</Button>
      )}
    </div>
  );
}

function ClaimantPanel({ h, reload }) {
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const send = useCallback(async (body) => {
    setBusy(true);
    try {
      const { data } = await api.post("/handovers/scan", body);
      toast.success(data.status === "completed" ? "Item returned. Receipt issued." : "Receipt confirmed. Waiting for the finder to confirm.");
      reload();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  }, [reload]);
  if (h.claimant_confirmed_at) return null;
  return (
    <div className="rounded-xl border border-slate-200 p-5 space-y-4" data-testid="claimant-scan-panel">
      <p className="text-sm text-slate-600">When you have the item in hand, scan the finder's QR code or type the 6-digit code they show you.</p>
      <QrScanner onToken={(t) => send({ token: t })} />
      <form onSubmit={(e) => { e.preventDefault(); send({ handover_id: h.id, code }); }} className="flex gap-2">
        <Input value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} placeholder="6-digit code" className="font-mono tracking-widest" data-testid="handover-code-input" />
        <Button type="submit" disabled={busy || code.length !== 6} className="bg-indigo-600 hover:bg-indigo-700" data-testid="handover-code-submit">Confirm</Button>
      </form>
    </div>
  );
}

export default function Handover() {
  const { id } = useParams();
  const [h, setH] = useState(null);
  const [err, setErr] = useState("");
  const load = useCallback(() => api.get(`/handovers/${id}`).then((r) => setH(r.data)).catch((e) => setErr(errMsg(e))), [id]);
  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  const cancel = async () => {
    if (!window.confirm("Cancel this handover? The claim will be cancelled.")) return;
    try {
      await api.post(`/handovers/${id}/cancel`);
      load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  if (err) return <div className="py-20 text-center text-slate-500" data-testid="handover-error">{err}</div>;
  if (!h) return <Spinner />;
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10" data-testid="handover-page">
      <span className="overline-label">Secure handover</span>
      <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 mt-1">QR handover</h1>
      <div className="card-surface p-6 mt-6 space-y-5">
        <div className="flex gap-4 items-center">
          <ItemThumb item={h.item} className="h-16 w-16 rounded-xl" />
          <div className="flex-1">
            <Link to={`/items/${h.item.id}`} className="font-semibold text-slate-900">{h.item.title}</Link>
            <div className="text-xs text-slate-500">Finder: {h.finder_name} · Owner: {h.claimant_name} · You are the <b data-testid="handover-role">{h.role}</b></div>
          </div>
          <span className="text-xs font-bold rounded-full px-2.5 py-1 bg-slate-100" data-testid="handover-status">{h.status}</span>
        </div>
        <div className="rounded-xl bg-teal-50 border border-teal-200 p-4 text-sm">
          <div className="font-semibold text-teal-800 flex items-center gap-2"><MapPin className="h-4 w-4" />Meet at</div>
          <div className="text-teal-900">{h.secure_collection_location || "Agree on a staffed campus location"}{h.collection_window ? ` · ${h.collection_window}` : ""}</div>
        </div>
        <div className="grid sm:grid-cols-3 gap-3">
          <Step done label="Claim approved" testId="step-approved" />
          <Step done={!!h.claimant_confirmed_at} label="Owner confirmed receipt" testId="step-claimant" />
          <Step done={!!h.finder_confirmed_at} label="Finder confirmed handover" testId="step-finder" />
        </div>
        {h.status === "completed" ? (
          <div className="rounded-xl bg-green-50 border border-green-200 p-5 text-center" data-testid="handover-complete">
            <ShieldCheck className="h-10 w-10 text-green-600 mx-auto" />
            <div className="font-bold text-green-900 mt-2">Item returned</div>
            {h.receipt && <Button asChild className="mt-3" data-testid="view-receipt-btn"><Link to={`/receipts/${h.receipt.id}`}>View receipt {h.receipt.receipt_no}</Link></Button>}
          </div>
        ) : h.status === "active" ? (
          <>
            {h.role === "finder" && <FinderPanel h={h} reload={load} />}
            {h.role === "claimant" && <ClaimantPanel h={h} reload={load} />}
            {h.role === "admin" && <p className="text-sm text-slate-500">Use the admin dashboard to complete this handover manually if scanning is unavailable.</p>}
            <p className="text-xs text-slate-500">Scanning alone never marks an item returned — both participants must confirm. Need help? An administrator can complete an assisted handover.</p>
            <Button variant="ghost" size="sm" className="text-red-600" onClick={cancel} data-testid="handover-cancel-btn"><XCircle className="h-4 w-4 mr-1" />Cancel handover</Button>
          </>
        ) : <p className="text-sm text-slate-500" data-testid="handover-cancelled">This handover was {h.status}.</p>}
      </div>
    </div>
  );
}
