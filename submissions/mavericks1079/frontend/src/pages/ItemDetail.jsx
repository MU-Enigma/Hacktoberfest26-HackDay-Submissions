import { useCallback, useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { MapPin, Clock, Lock, Building2, Gift, KeyRound, QrCode, XCircle, History, Info } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { StatusBadge, TypePill } from "@/components/StatusBadge";
import { ItemThumb } from "@/components/ItemCard";
import { Spinner } from "@/components/ProtectedRoute";
import { ReportAbuseDialog } from "@/components/ReportAbuseDialog";
import { MatchesPanel } from "@/components/item/MatchesPanel";
import { ClaimsReview } from "@/components/item/ClaimsReview";
import { ClaimDialog } from "@/components/item/ClaimDialog";
import { EditItemDialog } from "@/components/item/EditItemDialog";
import { useAuth } from "@/context/AuthContext";
import { api, errMsg, fmtDate } from "@/lib/api";
import { CATEGORY_LABELS, CLAIM_STYLE } from "@/lib/constants";

const Detail = ({ icon: Icon, label, value }) => (
  <div className="flex gap-3 items-start"><Icon className="h-4 w-4 mt-0.5 text-slate-400" /><div><div className="text-xs text-slate-500">{label}</div><div className="text-sm font-medium text-slate-900">{value}</div></div></div>
);

function Timeline({ history }) {
  return (
    <section className="card-surface p-6" data-testid="status-timeline">
      <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2"><History className="h-5 w-5 text-indigo-600" />Status history</h2>
      <ol className="mt-4 border-l-2 border-slate-200 ml-2 space-y-4">
        {history.map((h, i) => (
          <li key={i} className="pl-4 relative">
            <span className="absolute -left-[7px] top-1 h-3 w-3 rounded-full bg-indigo-500 ring-4 ring-white" />
            <StatusBadge status={h.status} testId={`history-status-${i}`} />
            <div className="text-xs text-slate-500 mt-1">{fmtDate(h.at)}{h.note ? ` · ${h.note}` : ""}</div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function ClaimantBox({ item, onClaim, reload }) {
  const c = item.my_claim;
  const cancel = async () => {
    try {
      await api.post(`/claims/${c.id}/cancel`);
      toast.success("Claim cancelled");
      reload();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  if (c && ["pending", "verifying", "approved"].includes(c.status)) {
    return (
      <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4 space-y-3" data-testid="my-claim-box">
        <div className="text-sm">Your claim status: <span className={`font-bold rounded-full px-2 py-0.5 text-xs ${CLAIM_STYLE[c.status]}`} data-testid="my-claim-status">{c.status}</span></div>
        <div className="flex gap-2 flex-wrap">
          {c.status === "approved" && <Button size="sm" asChild data-testid="my-claim-handover-btn"><Link to="/my-reports?tab=handovers"><QrCode className="h-4 w-4 mr-1" />Go to handover</Link></Button>}
          <Button size="sm" variant="outline" onClick={cancel} data-testid="my-claim-cancel-btn">Cancel claim</Button>
        </div>
      </div>
    );
  }
  const closed = ["RETURNED", "CLOSED", "READY FOR HANDOVER"].includes(item.status);
  return (
    <div className="space-y-2">
      {c && <p className="text-xs text-slate-500" data-testid="my-claim-last">Your last claim was {c.status}.</p>}
      <Button disabled={closed} onClick={onClaim} className="w-full h-12 rounded-full bg-indigo-600 hover:bg-indigo-700 font-bold" data-testid="claim-item-btn">
        <KeyRound className="h-4 w-4 mr-2" />This is mine — start a claim
      </Button>
      <p className="text-xs text-slate-500">You'll be asked for identifying details the finder can check privately.</p>
    </div>
  );
}

export default function ItemDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const [item, setItem] = useState(null);
  const [err, setErr] = useState("");
  const [claimOpen, setClaimOpen] = useState(false);
  const [v, setV] = useState(0);

  const load = useCallback(() => {
    api.get(`/items/${id}`).then((r) => setItem(r.data)).catch((e) => setErr(errMsg(e)));
    setV((x) => x + 1);
  }, [id]);
  useEffect(() => {
    load();
  }, [load]);

  const close = async () => {
    if (!window.confirm("Close this report? It will no longer be matched.")) return;
    try {
      await api.post(`/items/${id}/close`);
      load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  if (err) return <div className="max-w-3xl mx-auto px-4 py-20 text-center text-slate-500" data-testid="item-error">{err}</div>;
  if (!item) return <Spinner />;
  const active = !["RETURNED", "CLOSED"].includes(item.status);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10" data-testid="item-detail-page">
      <div className="grid lg:grid-cols-[1.1fr_1fr] gap-8">
        <div className="space-y-4">
          <ItemThumb item={item} className="w-full h-80 sm:h-96 rounded-2xl" />
          {item.image_paths?.length > 1 && <div className="flex gap-2">{item.image_paths.slice(1).map((p) => <ItemThumb key={p} item={{ ...item, image_paths: [p] }} className="h-20 w-20 rounded-lg" />)}</div>}
        </div>
        <div className="space-y-5">
          <div className="flex items-center gap-2 flex-wrap"><TypePill type={item.type} /><StatusBadge status={item.status} testId="item-status" /></div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900" data-testid="item-title">{item.title}</h1>
          <div className="text-sm font-semibold text-indigo-600" data-testid="item-category">{CATEGORY_LABELS[item.category]}
            {item.prediction_confidence != null && <span className="text-slate-400 font-normal"> · ML suggested {CATEGORY_LABELS[item.predicted_category]} ({Math.round(item.prediction_confidence * 100)}%)</span>}
          </div>
          <p className="text-slate-600 leading-relaxed" data-testid="item-description">{item.description}</p>
          <div className="grid sm:grid-cols-2 gap-4 card-surface p-5">
            <Detail icon={MapPin} label={item.type === "lost" ? "Last seen" : "Found at"} value={item.location} />
            <Detail icon={Clock} label={item.type === "lost" ? "Lost around" : "Found on"} value={fmtDate(item.occurred_at)} />
            {item.color && <Detail icon={Info} label="Colour" value={item.color} />}
            {item.attributes && <Detail icon={Info} label="Characteristics" value={item.attributes} />}
            {item.type === "found" && <Detail icon={Building2} label="Currently with" value={item.holder === "office" ? "An authorized campus office" : "The finder"} />}
            {item.collection_window && <Detail icon={Clock} label="Collection window" value={item.collection_window} />}
            {item.reward && <Detail icon={Gift} label="Reward" value={item.reward} />}
            {item.notes_for_owner && <Detail icon={Info} label="Note for owner" value={item.notes_for_owner} />}
          </div>
          {item.secure_collection_location && (
            <div className="rounded-xl bg-teal-50 border border-teal-200 p-4 text-sm" data-testid="secure-location">
              <div className="font-semibold text-teal-800 flex items-center gap-2"><Lock className="h-4 w-4" />Secure collection location</div>
              <div className="text-teal-900 mt-1">{item.secure_collection_location}</div>
            </div>
          )}
          {item.is_owner && (
            <div className="rounded-xl bg-slate-900 text-slate-100 p-4 text-sm" data-testid="private-clues-box">
              <div className="font-semibold flex items-center gap-2"><Lock className="h-4 w-4" />Private ownership clues (only you can see this)</div>
              <div className="mt-1 text-slate-300">{item.private_clues || "None stored. Add some so you can verify claimants."}</div>
            </div>
          )}
          {!user && item.type === "found" && active && (
            <Button onClick={() => nav(`/login?next=/items/${id}`)} className="w-full h-12 rounded-full bg-indigo-600" data-testid="login-to-claim-btn">Log in to claim this item</Button>
          )}
          {user && !item.is_owner && item.type === "found" && <ClaimantBox item={item} onClaim={() => setClaimOpen(true)} reload={load} />}
          <div className="flex gap-2 flex-wrap">
            {item.is_owner && active && <EditItemDialog item={item} onSaved={load} />}
            {item.is_owner && active && <Button size="sm" variant="outline" onClick={close} data-testid="item-close-btn"><XCircle className="h-4 w-4 mr-1.5" />Close report</Button>}
            {!item.is_owner && <ReportAbuseDialog targetType="item" targetId={item.id} />}
          </div>
        </div>
      </div>
      <div className="mt-10 grid lg:grid-cols-2 gap-6">
        {item.is_owner && <MatchesPanel key={`m${v}`} itemId={item.id} />}
        {(item.is_owner || user?.role === "admin") && item.type === "found" && <ClaimsReview key={`c${v}`} itemId={item.id} onChange={load} />}
        <Timeline history={item.status_history || []} />
      </div>
      {user && item.type === "found" && <ClaimDialog item={item} open={claimOpen} onOpenChange={setClaimOpen} onDone={load} />}
    </div>
  );
}
