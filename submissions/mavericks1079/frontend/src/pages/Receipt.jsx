import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { BadgeCheck, Printer } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Spinner } from "@/components/ProtectedRoute";
import { Logo } from "@/components/Navbar";
import { api, errMsg, fmtDate } from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/constants";

export default function Receipt() {
  const { id } = useParams();
  const [r, setR] = useState(null);
  const [err, setErr] = useState("");
  const load = () => api.get(`/receipts/${id}`).then((x) => setR(x.data)).catch((e) => setErr(errMsg(e)));
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (err) return <div className="py-20 text-center text-slate-500" data-testid="receipt-error">{err}</div>;
  if (!r) return <Spinner />;
  const rows = [["Receipt ID", r.receipt_no], ["Item", r.item_title], ["Item reference", r.item_id], ["Category", CATEGORY_LABELS[r.item_category]],
    ["Location", r.item_location], ["Finder", r.finder_name], ["Owner", r.claimant_name], ["Method", r.method], ["Completed", fmtDate(r.completed_at)], ["Status", r.transaction_status]];
  return (
    <div className="max-w-xl mx-auto px-4 py-10" data-testid="receipt-page">
      <div className="card-surface p-8">
        <div className="flex justify-between items-center"><Logo /><BadgeCheck className="h-8 w-8 text-green-600" /></div>
        <h1 className="text-2xl font-bold text-slate-900 mt-6">Handover receipt</h1>
        <dl className="mt-4 divide-y divide-slate-100 text-sm">
          {rows.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 py-2"><dt className="text-slate-500">{k}</dt><dd className="font-medium text-slate-900 text-right break-all" data-testid={`receipt-${k.toLowerCase().replace(/\s/g, "-")}`}>{v}</dd></div>
          ))}
        </dl>
        {r.admin_reason && <p className="text-xs text-slate-500 mt-3">Admin-assisted: {r.admin_reason}</p>}
        <label className="mt-6 flex items-center justify-between text-sm no-print">
          Hide this recovery from anonymized community success stories
          <Switch checked={r.my_story_opt_out} onCheckedChange={async (v) => { await api.post(`/receipts/${id}/story`, { opt_out: v }); load(); }} data-testid="story-optout-switch" />
        </label>
        <Button variant="outline" className="mt-6 no-print" onClick={() => window.print()} data-testid="receipt-print-btn"><Printer className="h-4 w-4 mr-2" />Print</Button>
      </div>
    </div>
  );
}
