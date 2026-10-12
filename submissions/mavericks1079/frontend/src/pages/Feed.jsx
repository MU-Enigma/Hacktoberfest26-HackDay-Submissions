import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Undo2, Sparkles } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ItemCard, EmptyState } from "@/components/ItemCard";
import { Spinner } from "@/components/ProtectedRoute";
import { ReportAbuseDialog } from "@/components/ReportAbuseDialog";
import { FilterSelect, useLocations } from "@/pages/Browse";
import { api, timeAgo } from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/constants";

const Row = ({ title, items, testId }) => (
  <section className="mt-10" data-testid={testId}>
    <h2 className="text-xl font-bold text-slate-900 mb-4">{title}</h2>
    {items.length === 0 ? <p className="text-sm text-slate-400">Nothing here yet.</p> : (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {items.slice(0, 8).map((i) => <ItemCard key={i.id} item={i} />)}
      </div>
    )}
  </section>
);

export default function Feed() {
  const locs = useLocations();
  const [f, setF] = useState({ category: "", location: "", q: "", since: "", sort: "" });
  const [q, setQ] = useState("");
  const [data, setData] = useState(null);

  useEffect(() => {
    setData(null);
    const p = Object.fromEntries(Object.entries(f).filter(([, v]) => v));
    if (p.since) p.since = new Date(Date.now() - Number(p.since) * 86400000).toISOString();
    api.get("/feed", { params: p }).then((r) => setData(r.data)).catch(() => setData(null));
  }, [f]);

  const s = data?.stats || {};
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10" data-testid="feed-page">
      <span className="overline-label">Community</span>
      <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 mt-1">Recovery feed</h1>
      <div className="mt-6 flex flex-wrap gap-2">
        <form onSubmit={(e) => { e.preventDefault(); setF({ ...f, q }); }} className="flex gap-2 flex-1 min-w-[240px]">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search the feed" className="pl-9 h-10 bg-white" data-testid="feed-search-input" />
          </div>
          <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700" data-testid="feed-search-btn">Search</Button>
        </form>
        <FilterSelect value={f.category} onChange={(v) => setF({ ...f, category: v })} placeholder="All categories" options={Object.entries(CATEGORY_LABELS)} testId="feed-filter-category" />
        <FilterSelect value={f.location} onChange={(v) => setF({ ...f, location: v })} placeholder="All locations" options={locs.map((l) => [l.name, l.name])} testId="feed-filter-location" />
        <FilterSelect value={f.since} onChange={(v) => setF({ ...f, since: v })} placeholder="Any date" options={[["1", "Last 24 hours"], ["7", "Last 7 days"], ["30", "Last 30 days"]]} testId="feed-filter-date" />
        <FilterSelect value={f.sort} onChange={(v) => setF({ ...f, sort: v })} placeholder="Newest first" options={[["oldest", "Oldest first"]]} testId="feed-filter-sort" />
      </div>
      {!data ? <Spinner /> : (
        <>
          <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="feed-stats">
            {[["Lost", s.lost], ["Found", s.found], ["Returned", s.returned], ["Recovery rate", `${s.recovery_rate ?? 0}%`]].map(([l, v]) => (
              <div key={l} className="card-surface p-4"><div className="text-2xl font-extrabold text-slate-900">{v}</div><div className="text-xs text-slate-500">{l}</div></div>
            ))}
          </div>
          <section className="mt-10" data-testid="feed-matches">
            <h2 className="text-xl font-bold text-slate-900 mb-4">Potential matches</h2>
            {data.matches.length === 0 ? <EmptyState icon={Sparkles} title="No matches yet" /> : (
              <div className="grid md:grid-cols-2 gap-3">
                {data.matches.map((m) => (
                  <div key={m.id} className="card-surface p-4 flex items-center gap-3">
                    <span className="font-mono font-bold text-indigo-700 bg-indigo-50 rounded-lg px-2 py-1 text-sm">{m.score}%</span>
                    <div className="text-sm text-slate-700 min-w-0">
                      <Link to={`/items/${m.lost.id}`} className="font-semibold hover:text-indigo-700 truncate block">Lost: {m.lost.title}</Link>
                      <Link to={`/items/${m.found.id}`} className="text-slate-500 hover:text-indigo-700 truncate block">Found: {m.found.title}</Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
          <Row title="Recently lost" items={data.lost} testId="feed-lost" />
          <Row title="Recently found" items={data.found} testId="feed-found" />
          <Row title="Recently recovered" items={data.recovered} testId="feed-recovered" />
          <section className="mt-10" data-testid="feed-stories">
            <h2 className="text-xl font-bold text-slate-900 mb-4">Success stories (anonymized)</h2>
            {data.stories.length === 0 ? <EmptyState icon={Undo2} title="No stories yet" /> : (
              <div className="grid md:grid-cols-2 gap-3">
                {data.stories.map((st) => (
                  <div key={st.id} className="card-surface p-4 text-sm text-slate-700 flex items-center gap-3">
                    <Undo2 className="h-5 w-5 text-green-600 shrink-0" />
                    A {st.category_label} item found near {st.location} was returned · {timeAgo(st.completed_at)}
                  </div>
                ))}
              </div>
            )}
          </section>
          <div className="mt-10 flex justify-end"><ReportAbuseDialog targetType="other" label="Report something in the feed" /></div>
        </>
      )}
    </div>
  );
}
