import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { FileText, KeyRound, QrCode, Receipt as ReceiptIcon, PlusCircle } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ItemCard, EmptyState, ItemThumb } from "@/components/ItemCard";
import { Spinner } from "@/components/ProtectedRoute";
import { api, fmtDate } from "@/lib/api";
import { CLAIM_STYLE } from "@/lib/constants";

const Row = ({ to, item, right, testId, sub }) => (
  <Link to={to} className="card-surface p-4 flex items-center gap-4 hover:shadow-md transition-shadow" data-testid={testId}>
    {item && <ItemThumb item={item} className="h-14 w-14 rounded-lg shrink-0" />}
    <div className="flex-1 min-w-0">
      <div className="font-semibold text-slate-900 truncate">{item?.title || "Item"}</div>
      <div className="text-xs text-slate-500">{sub}</div>
    </div>
    {right}
  </Link>
);

function useData(url) {
  const [d, setD] = useState(null);
  useEffect(() => {
    api.get(url).then((r) => setD(r.data)).catch(() => setD([]));
  }, [url]);
  return d;
}

export default function MyReports() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") || "reports";
  const items = useData("/items/mine");
  const claims = useData("/claims/mine");
  const handovers = useData("/handovers/mine");
  const receipts = useData("/receipts/mine");

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10" data-testid="my-reports-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><span className="overline-label">Your activity</span><h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 mt-1">My reports</h1></div>
        <div className="flex gap-2">
          <Button asChild className="rounded-full bg-amber-500 hover:bg-amber-600" data-testid="my-report-lost-btn"><Link to="/report/lost"><PlusCircle className="h-4 w-4 mr-1" />I lost it</Link></Button>
          <Button asChild className="rounded-full bg-emerald-600 hover:bg-emerald-700" data-testid="my-report-found-btn"><Link to="/report/found"><PlusCircle className="h-4 w-4 mr-1" />I found it</Link></Button>
        </div>
      </div>
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v })} className="mt-6">
        <TabsList className="flex-wrap h-auto">
          <TabsTrigger value="reports" data-testid="tab-reports">Reports</TabsTrigger>
          <TabsTrigger value="claims" data-testid="tab-claims">My claims</TabsTrigger>
          <TabsTrigger value="handovers" data-testid="tab-handovers">Handovers</TabsTrigger>
          <TabsTrigger value="receipts" data-testid="tab-receipts">Receipts</TabsTrigger>
        </TabsList>
        <TabsContent value="reports" className="mt-6">
          {!items ? <Spinner /> : items.length === 0 ? <EmptyState icon={FileText} title="No reports yet" text="Report something you lost or found." /> : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {items.map((i) => <ItemCard key={i.id} item={i} extra={<span className="text-[11px] text-slate-500">{i.match_count} match · {i.open_claims} claim</span>} />)}
            </div>
          )}
        </TabsContent>
        <TabsContent value="claims" className="mt-6 space-y-3">
          {!claims ? <Spinner /> : claims.length === 0 ? <EmptyState icon={KeyRound} title="No claims yet" /> : claims.map((c) => (
            <Row key={c.id} to={c.handover?.status === "active" ? `/handover/${c.handover.id}` : `/items/${c.item_id}`} item={c.item} testId={`my-claim-${c.id}`} sub={`Submitted ${fmtDate(c.created_at)}`}
              right={<span className={`text-xs font-bold rounded-full px-2.5 py-0.5 ${CLAIM_STYLE[c.status]}`}>{c.status}</span>} />
          ))}
        </TabsContent>
        <TabsContent value="handovers" className="mt-6 space-y-3">
          {!handovers ? <Spinner /> : handovers.length === 0 ? <EmptyState icon={QrCode} title="No handovers yet" text="Approved claims create a secure handover session." /> : handovers.map((h) => (
            <Row key={h.id} to={`/handover/${h.id}`} item={h.item} testId={`my-handover-${h.id}`} sub={`You are the ${h.role} · ${fmtDate(h.created_at)}`}
              right={<span className="text-xs font-bold rounded-full px-2.5 py-0.5 bg-slate-100 text-slate-700">{h.status}</span>} />
          ))}
        </TabsContent>
        <TabsContent value="receipts" className="mt-6 space-y-3">
          {!receipts ? <Spinner /> : receipts.length === 0 ? <EmptyState icon={ReceiptIcon} title="No receipts yet" /> : receipts.map((r) => (
            <Row key={r.id} to={`/receipts/${r.id}`} item={{ title: r.item_title }} testId={`my-receipt-${r.id}`} sub={`${r.receipt_no} · ${fmtDate(r.completed_at)}`}
              right={<span className="text-xs font-bold rounded-full px-2.5 py-0.5 bg-green-100 text-green-800">{r.transaction_status}</span>} />
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
}
