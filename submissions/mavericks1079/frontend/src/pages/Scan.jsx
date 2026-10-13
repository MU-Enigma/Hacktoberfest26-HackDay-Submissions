import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ShieldCheck, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, errMsg } from "@/lib/api";

export default function Scan() {
  const [params] = useSearchParams();
  const token = params.get("t");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState(null);
  const [err, setErr] = useState("");

  const confirm = async () => {
    setBusy(true);
    setErr("");
    try {
      const { data } = await api.post("/handovers/scan", { token });
      setRes(data);
    } catch (e) {
      setErr(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 py-16 text-center" data-testid="scan-page">
      <ShieldCheck className="h-12 w-12 text-indigo-600 mx-auto" />
      <h1 className="text-2xl font-bold text-slate-900 mt-4">Confirm you received your item</h1>
      <p className="text-sm text-slate-500 mt-2">Only confirm once the item is physically in your hands. This code works once.</p>
      {!token && <p className="text-red-600 mt-4">No handover code found in this link.</p>}
      {res ? (
        <div className="card-surface p-5 mt-6" data-testid="scan-result">
          <p className="font-semibold text-slate-900">{res.status === "completed" ? "Handover complete!" : "Confirmed. Waiting for the finder to confirm."}</p>
          <Button asChild className="mt-3"><Link to={res.receipt_id ? `/receipts/${res.receipt_id}` : `/handover/${res.handover_id}`}>{res.receipt_id ? "View receipt" : "Open handover"}</Link></Button>
        </div>
      ) : token && (
        <Button onClick={confirm} disabled={busy} className="mt-6 h-12 rounded-full px-8 bg-emerald-600 hover:bg-emerald-700" data-testid="scan-confirm-btn">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Yes, I have received it"}
        </Button>
      )}
      {err && <p className="text-sm text-red-600 mt-4" data-testid="scan-error">{err}</p>}
    </div>
  );
}
