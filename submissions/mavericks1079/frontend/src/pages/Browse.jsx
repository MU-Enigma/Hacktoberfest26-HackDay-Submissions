import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, PackageSearch } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ItemCard, EmptyState } from "@/components/ItemCard";
import { Spinner } from "@/components/ProtectedRoute";
import { PhotoSearchButton, PhotoSearchResults } from "@/components/PhotoSearch";
import { api } from "@/lib/api";
import { CATEGORY_LABELS, STATUSES } from "@/lib/constants";

export const FilterSelect = ({ value, onChange, placeholder, options, testId }) => (
  <Select value={value || "all"} onValueChange={(v) => onChange(v === "all" ? "" : v)}>
    <SelectTrigger className="h-10 bg-white w-full sm:w-auto min-w-[150px]" data-testid={testId}><SelectValue placeholder={placeholder} /></SelectTrigger>
    <SelectContent>
      <SelectItem value="all">{placeholder}</SelectItem>
      {options.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}
    </SelectContent>
  </Select>
);

export const useLocations = () => {
  const [locs, setLocs] = useState([]);
  useEffect(() => {
    api.get("/locations").then((r) => setLocs(r.data)).catch(() => {});
  }, []);
  return locs;
};

export default function Browse() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get("q") || "");
  const [data, setData] = useState(null);
  const [limit, setLimit] = useState(24);
  const [photo, setPhoto] = useState(null);
  const [photoBusy, setPhotoBusy] = useState(false);
  const locs = useLocations();
  const f = Object.fromEntries(["type", "category", "location", "status", "sort"].map((k) => [k, params.get(k) || ""]));

  useEffect(() => {
    setData(null);
    const p = { ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)), q: params.get("q") || undefined, limit };
    api.get("/items", { params: p }).then((r) => setData(r.data)).catch(() => setData({ total: 0, items: [] }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params, limit]);

  const update = (k, v) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    setParams(next);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10" data-testid="browse-page">
      <span className="overline-label">Browse</span>
      <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 mt-1">Lost & found items</h1>
      <form onSubmit={(e) => { e.preventDefault(); update("q", q); }} className="mt-6 flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name, description, category or location" className="pl-9 h-11 bg-white" data-testid="browse-search-input" />
        </div>
        <Button type="submit" className="h-11 bg-indigo-600 hover:bg-indigo-700" data-testid="browse-search-btn">Search</Button>
        <PhotoSearchButton type={f.type} onResults={setPhoto} busy={photoBusy} setBusy={setPhotoBusy} />
      </form>
      <div className="mt-4 flex flex-wrap gap-2">
        <FilterSelect value={f.type} onChange={(v) => update("type", v)} placeholder="Lost & found" options={[["lost", "Lost"], ["found", "Found"]]} testId="filter-type" />
        <FilterSelect value={f.category} onChange={(v) => update("category", v)} placeholder="All categories" options={Object.entries(CATEGORY_LABELS)} testId="filter-category" />
        <FilterSelect value={f.location} onChange={(v) => update("location", v)} placeholder="All locations" options={locs.map((l) => [l.name, l.name])} testId="filter-location" />
        <FilterSelect value={f.status} onChange={(v) => update("status", v)} placeholder="Any status" options={STATUSES.map((s) => [s, s])} testId="filter-status" />
        <FilterSelect value={f.sort} onChange={(v) => update("sort", v)} placeholder="Newest first" options={[["oldest", "Oldest first"]]} testId="filter-sort" />
      </div>
      {photo && <PhotoSearchResults data={photo} onClear={() => setPhoto(null)} />}
      <div className="mt-8">
        {!data ? <Spinner /> : data.items.length === 0 ? (
          <EmptyState icon={PackageSearch} title="No items match your search" text="Try different keywords or clear filters." />
        ) : (
          <>
            <p className="text-sm text-slate-500 mb-4" data-testid="browse-total">{data.total} item(s)</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">{data.items.map((i) => <ItemCard key={i.id} item={i} />)}</div>
            {data.total > data.items.length && (
              <div className="text-center mt-8"><Button variant="outline" onClick={() => setLimit(limit + 24)} data-testid="browse-load-more">Load more</Button></div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
