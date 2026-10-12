import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Gavel, QrCode } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ReportAbuseDialog } from "@/components/ReportAbuseDialog";
import { api, errMsg, fmtDate } from "@/lib/api";
import { CLAIM_STYLE } from "@/lib/constants";

const SCORE_STYLE = { Strong: "text-emerald-700 bg-emerald-50", Partial: "text-amber-700 bg-amber-50", Weak: "text-red-700 bg-red-50" };

export function ClaimsReview({ itemId, onChange }) {
  const [claims, setClaims] = useState(null);
  const load = () => api.get(`/items/${itemId}/claims`).then((r) => setClaims(r.data)).catch(() => setClaims([]));
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itemId]);

  const act = async (id, action) => {
    try {
      await api.post(`/claims/${id}/review`, { action });
      toast.success(action === "approve" ? "Claim approved. A handover session was created." : action === "reject" ? "Claim rejected" : "Marked as verification in progress");
      load();
      onChange?.();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  if (!claims) return null;
  return (
    <section className="card-surface p-6" data-testid="claims-review">
      <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2"><Gavel className="h-5 w-5 text-indigo-600" />Ownership claims</h2>
      <p className="text-xs text-slate-500 mt-1">Compare each claimant's details with your private clues. For high-value items, verify at a campus office.</p>
      {claims.length === 0 ? <p className="text-sm text-slate-500 mt-4">No claims yet.</p> : (
        <div className="mt-4 space-y-3">
          {claims.map((c) => {
            const label = c.score_label.split(" ")[0];
            return (
              <div key={c.id} className="rounded-xl border border-slate-200 p-4" data-testid={`claim-${c.id}`}>
                <div className="flex flex-wrap items-center gap-2 justify-between">
                  <div className="font-semibold text-slate-900">{c.claimant_name}</div>
                  <span className={`text-xs font-bold rounded-full px-2.5 py-0.5 ${CLAIM_STYLE[c.status]}`} data-testid={`claim-status-${c.id}`}>{c.status}</span>
                </div>
                <div className="text-xs text-slate-400">{fmtDate(c.created_at)} · attempts on this item: {c.attempts}</div>
                <dl className="mt-3 text-sm space-y-1">
                  <div><dt className="inline text-slate-500">Distinctive marks: </dt><dd className="inline text-slate-800">{c.marks}</dd></div>
                  {c.contents && <div><dt className="inline text-slate-500">Contents: </dt><dd className="inline text-slate-800">{c.contents}</dd></div>}
                  <div><dt className="inline text-slate-500">How/when lost: </dt><dd className="inline text-slate-800">{c.circumstances}</dd></div>
                </dl>
                <div className={`mt-3 inline-block text-xs font-semibold rounded-lg px-2 py-1 ${SCORE_STYLE[label] || "bg-slate-100 text-slate-600"}`} data-testid={`claim-score-${c.id}`}>
                  Clue agreement: {c.verification_score ?? "n/a"}{c.verification_score != null ? "/100" : ""} · {c.score_label}
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {c.status === "pending" && <Button size="sm" variant="outline" onClick={() => act(c.id, "start_verification")} data-testid={`claim-verify-${c.id}`}>Start verification</Button>}
                  {["pending", "verifying"].includes(c.status) && (
                    <>
                      <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700" onClick={() => act(c.id, "approve")} data-testid={`claim-approve-${c.id}`}>Approve</Button>
                      <Button size="sm" variant="outline" className="text-red-600" onClick={() => act(c.id, "reject")} data-testid={`claim-reject-${c.id}`}>Reject</Button>
                    </>
                  )}
                  {c.handover && <Button size="sm" asChild data-testid={`claim-handover-${c.id}`}><Link to={`/handover/${c.handover.id}`}><QrCode className="h-4 w-4 mr-1" />Handover ({c.handover.status})</Link></Button>}
                  <ReportAbuseDialog targetType="claim" targetId={c.id} label="Report claim" />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
