import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/StatusBadge";
import { FilterSelect } from "@/pages/Browse";
import { api, errMsg, fmtDate } from "@/lib/api";
import { CATEGORY_LABELS, CLAIM_STYLE, STATUSES } from "@/lib/constants";

function useList(url, deps = []) {
  const [d, setD] = useState([]);
  const load = () => api.get(url).then((r) => setD(r.data)).catch((e) => toast.error(errMsg(e)));
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, ...deps]);
  return [d, load];
}

const ask = (msg) => {
  const r = window.prompt(msg);
  return r && r.trim().length >= 3 ? r.trim() : null;
};

const run = async (fn, ok, after) => {
  try {
    await fn();
    toast.success(ok);
    after?.();
  } catch (e) {
    toast.error(errMsg(e));
  }
};

const Box = ({ children, testId }) => <div className="card-surface p-4 text-sm" data-testid={testId}>{children}</div>;

function Overview() {
  const [s, setS] = useState({});
  useEffect(() => {
    api.get("/admin/stats").then((r) => setS(r.data));
  }, []);
  const cells = [["Lost", s.lost], ["Found", s.found], ["Returned", s.returned], ["Recovery rate", `${s.recovery_rate ?? 0}%`], ["Open misuse reports", s.open_reports],
    ["Open claims", s.open_claims], ["Active handovers", s.active_handovers], ["Suspended", s.suspended], ["Banned", s.banned], ["Open appeals", s.open_appeals]];
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4" data-testid="admin-overview">
      {cells.map(([l, v]) => <div key={l} className="card-surface p-4"><div className="text-2xl font-extrabold">{v ?? "-"}</div><div className="text-xs text-slate-500">{l}</div></div>)}
    </div>
  );
}

function Reports() {
  const [status, setStatus] = useState("");
  const [rows, load] = useList(`/admin/reports${status ? `?status=${status}` : ""}`);
  const resolve = (id, st) => run(() => api.post(`/admin/reports/${id}/resolve`, { status: st, note: window.prompt("Resolution note (optional)") || "" }), "Report updated", load);
  return (
    <div className="space-y-3">
      <FilterSelect value={status} onChange={setStatus} placeholder="All statuses" options={[["open", "Open"], ["in_review", "In review"], ["actioned", "Actioned"], ["dismissed", "Dismissed"]]} testId="admin-report-filter" />
      {rows.length === 0 && <p className="text-sm text-slate-500">No reports.</p>}
      {rows.map((r) => (
        <Box key={r.id} testId={`admin-report-${r.id}`}>
          <div className="flex flex-wrap justify-between gap-2">
            <div className="font-semibold">{r.reason}</div>
            <span className="text-xs font-bold rounded-full px-2 py-0.5 bg-slate-100">{r.status}{r.source === "automated" ? " · automated flag" : ""}</span>
          </div>
          <div className="text-slate-600 mt-1">{r.details}</div>
          <div className="text-xs text-slate-500 mt-1">Target: {r.target_type} {r.target_id ? `(${r.target_id.slice(0, 8)})` : ""} · user: {r.target_user_name || "-"} · by {r.reporter_name || "-"} · {fmtDate(r.created_at)}</div>
          <div className="mt-2 flex gap-2 flex-wrap">
            {r.target_type === "item" && r.target_id && <Button size="sm" variant="outline" asChild><Link to={`/items/${r.target_id}`}>Open item</Link></Button>}
            <Button size="sm" variant="outline" onClick={() => resolve(r.id, "in_review")} data-testid={`report-review-${r.id}`}>In review</Button>
            <Button size="sm" variant="outline" onClick={() => resolve(r.id, "actioned")} data-testid={`report-action-${r.id}`}>Actioned</Button>
            <Button size="sm" variant="outline" onClick={() => resolve(r.id, "dismissed")} data-testid={`report-dismiss-${r.id}`}>Dismiss</Button>
          </div>
        </Box>
      ))}
    </div>
  );
}

function Users() {
  const [q, setQ] = useState("");
  const [rows, load] = useList(`/admin/users${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  const act = (u, action) => {
    const reason = ask(`Reason for ${action} (required, min 5 chars)`);
    if (!reason) return;
    const days = action === "suspend" ? Number(window.prompt("Suspension length in days", "7")) || 7 : undefined;
    run(() => api.post(`/admin/users/${u.id}/action`, { action, reason, days }), `User ${action} recorded`, load);
  };
  return (
    <div className="space-y-3">
      <Input placeholder="Search name or email" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-sm bg-white" data-testid="admin-user-search" />
      {rows.map((u) => (
        <Box key={u.id} testId={`admin-user-${u.id}`}>
          <div className="flex flex-wrap justify-between gap-2 items-center">
            <div><span className="font-semibold">{u.name}</span> <span className="text-slate-500">{u.email}</span> <span className="text-xs text-slate-400">· {u.role}</span></div>
            <span className={`text-xs font-bold rounded-full px-2 py-0.5 ${u.status === "active" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-700"}`} data-testid={`admin-user-status-${u.id}`}>{u.status}</span>
          </div>
          {u.role !== "admin" && (
            <div className="mt-2 flex gap-2 flex-wrap">
              <Button size="sm" variant="outline" onClick={() => act(u, "warn")} data-testid={`user-warn-${u.id}`}>Warn</Button>
              <Button size="sm" variant="outline" onClick={() => act(u, "suspend")} data-testid={`user-suspend-${u.id}`}>Suspend</Button>
              <Button size="sm" variant="outline" className="text-red-600" onClick={() => act(u, "ban")} data-testid={`user-ban-${u.id}`}>Ban</Button>
              {u.status !== "active" && <Button size="sm" onClick={() => act(u, "reinstate")} data-testid={`user-reinstate-${u.id}`}>Reinstate</Button>}
            </div>
          )}
        </Box>
      ))}
    </div>
  );
}

function Claims() {
  const [status, setStatus] = useState("");
  const [rows] = useList(`/admin/claims${status ? `?status=${status}` : ""}`);
  return (
    <div className="space-y-3">
      <FilterSelect value={status} onChange={setStatus} placeholder="All claims" options={Object.keys(CLAIM_STYLE).map((s) => [s, s])} testId="admin-claim-filter" />
      {rows.map((c) => (
        <Box key={c.id} testId={`admin-claim-${c.id}`}>
          <div className="flex justify-between gap-2"><Link to={`/items/${c.item_id}`} className="font-semibold hover:text-indigo-700">{c.item?.title}</Link><span className={`text-xs font-bold rounded-full px-2 py-0.5 ${CLAIM_STYLE[c.status]}`}>{c.status}</span></div>
          <div className="text-xs text-slate-500">Clue agreement {c.verification_score ?? "n/a"} · {fmtDate(c.created_at)} · Review from the item page</div>
        </Box>
      ))}
    </div>
  );
}

function Handovers() {
  const [rows, load] = useList("/admin/handovers");
  const complete = (h) => {
    const reason = ask("Admin-assisted completion: describe how ownership and the physical transfer were verified (min 5 chars)");
    if (reason) run(() => api.post(`/admin/handovers/${h.id}/complete`, { reason }), "Handover completed", load);
  };
  return (
    <div className="space-y-3">
      {rows.map((h) => (
        <Box key={h.id} testId={`admin-handover-${h.id}`}>
          <div className="flex justify-between gap-2"><span className="font-semibold">{h.item?.title}</span><span className="text-xs font-bold rounded-full px-2 py-0.5 bg-slate-100">{h.status}</span></div>
          <div className="text-xs text-slate-500">Owner confirmed: {h.claimant_confirmed_at ? fmtDate(h.claimant_confirmed_at) : "no"} · Finder confirmed: {h.finder_confirmed_at ? fmtDate(h.finder_confirmed_at) : "no"}</div>
          <ul className="text-xs text-slate-500 mt-1 list-disc pl-4">{h.events?.map((e, i) => <li key={i}>{e.event} · {fmtDate(e.at)}</li>)}</ul>
          {h.status === "active" && <Button size="sm" variant="outline" className="mt-2" onClick={() => complete(h)} data-testid={`admin-complete-${h.id}`}>Admin-assisted completion</Button>}
        </Box>
      ))}
    </div>
  );
}

function Appeals() {
  const [rows, load] = useList("/admin/appeals");
  const resolve = (a, decision) => {
    const note = ask("Decision note (required)");
    if (note) run(() => api.post(`/admin/appeals/${a.id}/resolve`, { decision, note }), "Appeal resolved", load);
  };
  return (
    <div className="space-y-3">
      {rows.length === 0 && <p className="text-sm text-slate-500">No appeals.</p>}
      {rows.map((a) => (
        <Box key={a.id} testId={`admin-appeal-${a.id}`}>
          <div className="flex justify-between"><span className="font-semibold">{a.user?.name} ({a.user?.status})</span><span className="text-xs font-bold">{a.status}</span></div>
          <p className="text-slate-600 mt-1">{a.message}</p>
          {a.status === "open" && (
            <div className="mt-2 flex gap-2">
              <Button size="sm" onClick={() => resolve(a, "overturned")} data-testid={`appeal-overturn-${a.id}`}>Overturn & reinstate</Button>
              <Button size="sm" variant="outline" onClick={() => resolve(a, "upheld")} data-testid={`appeal-uphold-${a.id}`}>Uphold decision</Button>
            </div>
          )}
        </Box>
      ))}
    </div>
  );
}

function Items() {
  const [status, setStatus] = useState("");
  const [rows, load] = useList(`/admin/items${status ? `?status=${encodeURIComponent(status)}` : ""}`);
  const close = (i) => {
    const reason = ask("Reason for closing");
    if (reason) run(() => api.post(`/admin/items/${i.id}/close`, { reason }), "Item closed", load);
  };
  return (
    <div className="space-y-3">
      <FilterSelect value={status} onChange={setStatus} placeholder="Any status" options={STATUSES.map((s) => [s, s])} testId="admin-item-filter" />
      {rows.map((i) => (
        <Box key={i.id} testId={`admin-item-${i.id}`}>
          <div className="flex flex-wrap justify-between gap-2 items-center">
            <Link to={`/items/${i.id}`} className="font-semibold hover:text-indigo-700">{i.type.toUpperCase()} · {i.title}</Link>
            <StatusBadge status={i.status} />
          </div>
          <div className="text-xs text-slate-500">{CATEGORY_LABELS[i.category]} · {i.location} · {fmtDate(i.created_at)}</div>
          {!["CLOSED", "RETURNED"].includes(i.status) && <Button size="sm" variant="outline" className="mt-2" onClick={() => close(i)} data-testid={`admin-close-item-${i.id}`}>Close report</Button>}
        </Box>
      ))}
    </div>
  );
}

function Locations() {
  const [rows, load] = useList("/locations");
  const [f, setF] = useState({ name: "", zone: "" });
  return (
    <div className="grid lg:grid-cols-2 gap-6">
      <div className="space-y-3">
        <form onSubmit={(e) => { e.preventDefault(); run(() => api.post("/admin/locations", { ...f, is_safe_point: false }), "Location added", () => { setF({ name: "", zone: "" }); load(); }); }} className="flex gap-2">
          <Input placeholder="Location name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className="bg-white" data-testid="admin-location-name" />
          <Input placeholder="Zone" value={f.zone} onChange={(e) => setF({ ...f, zone: e.target.value })} className="bg-white" data-testid="admin-location-zone" />
          <Button type="submit" data-testid="admin-location-add">Add</Button>
        </form>
        {rows.map((l) => (
          <Box key={l.id} testId={`admin-location-${l.id}`}>
            <div className="flex justify-between items-center"><span><b>{l.name}</b> <span className="text-slate-500">· {l.zone}{l.is_safe_point ? " · safe point" : ""}</span></span>
              <Button size="sm" variant="ghost" className="text-red-600" onClick={() => run(() => api.delete(`/admin/locations/${l.id}`), "Location removed", load)}>Remove</Button></div>
          </Box>
        ))}
      </div>
      <Box testId="admin-categories">
        <div className="font-semibold mb-2">ML categories</div>
        <p className="text-xs text-slate-500 mb-2">Categories are the classifier's label set. Adding one requires retraining with examples in backend/ml.py.</p>
        <ul className="space-y-1">{Object.entries(CATEGORY_LABELS).map(([k, v]) => <li key={k}>{v} <span className="text-xs text-slate-400 font-mono">{k}</span></li>)}</ul>
      </Box>
    </div>
  );
}

function Audit() {
  const [q, setQ] = useState("");
  const [rows] = useList(`/admin/audit${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  return (
    <div className="space-y-2">
      <Input placeholder="Filter by action (e.g. handover)" value={q} onChange={(e) => setQ(e.target.value)} className="max-w-sm bg-white" data-testid="admin-audit-filter" />
      <div className="card-surface overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-slate-50 text-slate-500"><tr><th className="text-left p-2">Time</th><th className="text-left p-2">Action</th><th className="text-left p-2">Target</th><th className="text-left p-2">Actor</th></tr></thead>
          <tbody>{rows.map((a) => <tr key={a.id} className="border-t border-slate-100"><td className="p-2 whitespace-nowrap">{fmtDate(a.created_at)}</td><td className="p-2 font-mono">{a.action}</td><td className="p-2">{a.target_type} {a.target_id?.slice(0, 8)}</td><td className="p-2 font-mono">{a.actor_id?.slice(0, 8)}</td></tr>)}</tbody>
        </table>
      </div>
    </div>
  );
}

const TABS = [["overview", "Overview", Overview], ["reports", "Misuse reports", Reports], ["claims", "Claims", Claims], ["users", "Users", Users], ["handovers", "Handovers", Handovers],
  ["appeals", "Appeals", Appeals], ["items", "Items", Items], ["locations", "Locations & categories", Locations], ["audit", "Audit log", Audit]];

export default function Admin() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10" data-testid="admin-page">
      <span className="overline-label">Administrators only</span>
      <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 mt-1">Admin dashboard</h1>
      <Tabs defaultValue="overview" className="mt-6">
        <TabsList className="flex-wrap h-auto">{TABS.map(([k, l]) => <TabsTrigger key={k} value={k} data-testid={`admin-tab-${k}`}>{l}</TabsTrigger>)}</TabsList>
        {TABS.map(([k, , C]) => <TabsContent key={k} value={k} className="mt-6"><C /></TabsContent>)}
      </Tabs>
    </div>
  );
}
