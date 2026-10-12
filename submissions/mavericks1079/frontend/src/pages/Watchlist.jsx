import { useEffect, useState } from "react";
import { Eye, Trash2, Pencil, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { EmptyState } from "@/components/ItemCard";
import { PhotoUpload } from "@/components/report/PhotoUpload";
import { FilterSelect, useLocations } from "@/pages/Browse";
import { api, errMsg, fileUrl } from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/constants";

const EMPTY = { name: "", keywords: "", category: "", color: "", locations: [], date_from: "", date_to: "", item_type: "found", threshold: 50, reference_image: null, active: true };

function WatchForm({ initial, onSaved, onCancel }) {
  const locs = useLocations();
  const [f, setF] = useState(initial || EMPTY);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e?.target ? e.target.value : e });

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const body = { ...f };
      delete body.id; delete body.user_id; delete body.created_at;
      if (initial?.id) await api.put(`/watchlists/${initial.id}`, body);
      else await api.post("/watchlists", body);
      toast.success("Watchlist saved");
      setF(EMPTY);
      onSaved();
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={save} className="card-surface p-6 space-y-4" data-testid="watchlist-form">
      <h2 className="font-bold text-slate-900">{initial?.id ? "Edit watchlist" : "New watchlist"}</h2>
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="space-y-1.5"><Label htmlFor="w-name">Name</Label><Input id="w-name" required value={f.name} onChange={set("name")} placeholder="My blue bottle" data-testid="watchlist-name-input" /></div>
        <div className="space-y-1.5"><Label htmlFor="w-kw">Keywords</Label><Input id="w-kw" value={f.keywords} onChange={set("keywords")} placeholder="bottle steel milton" data-testid="watchlist-keywords-input" /></div>
        <div className="space-y-1.5"><Label>Category</Label><FilterSelect value={f.category} onChange={set("category")} placeholder="Any category" options={Object.entries(CATEGORY_LABELS)} testId="watchlist-category-select" /></div>
        <div className="space-y-1.5"><Label htmlFor="w-color">Colour / characteristics</Label><Input id="w-color" value={f.color} onChange={set("color")} data-testid="watchlist-color-input" /></div>
        <div className="space-y-1.5"><Label>Report type</Label><FilterSelect value={f.item_type === "any" ? "" : f.item_type} onChange={(v) => setF({ ...f, item_type: v || "any" })} placeholder="Lost & found" options={[["found", "Found items"], ["lost", "Lost items"]]} testId="watchlist-type-select" /></div>
        <div className="space-y-1.5"><Label>Add campus location</Label>
          <FilterSelect value="" onChange={(v) => v && !f.locations.includes(v) && setF({ ...f, locations: [...f.locations, v] })} placeholder="Choose location" options={locs.map((l) => [l.name, l.name])} testId="watchlist-location-select" />
          <div className="flex flex-wrap gap-1">{f.locations.map((l) => <button type="button" key={l} onClick={() => setF({ ...f, locations: f.locations.filter((x) => x !== l) })} className="text-xs bg-indigo-50 text-indigo-700 rounded-full px-2 py-0.5">{l} ×</button>)}</div>
        </div>
        <div className="space-y-1.5"><Label htmlFor="w-from">From date</Label><Input id="w-from" type="date" value={f.date_from} onChange={set("date_from")} data-testid="watchlist-from-input" /></div>
        <div className="space-y-1.5"><Label htmlFor="w-to">To date</Label><Input id="w-to" type="date" value={f.date_to} onChange={set("date_to")} data-testid="watchlist-to-input" /></div>
      </div>
      <div className="space-y-2">
        <Label>Match threshold: <span className="font-mono">{f.threshold}%</span></Label>
        <Slider min={20} max={95} step={5} value={[f.threshold]} onValueChange={([v]) => setF({ ...f, threshold: v })} data-testid="watchlist-threshold-slider" />
      </div>
      <div className="space-y-1.5"><Label>Reference photo (optional, for your own reference)</Label>
        <PhotoUpload paths={f.reference_image ? [f.reference_image] : []} max={1} onChange={(p) => setF({ ...f, reference_image: p[0] || null })} testId="watchlist-photo" />
      </div>
      <div className="flex gap-2 justify-end">
        {onCancel && <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>}
        <Button type="submit" disabled={busy} className="bg-indigo-600 hover:bg-indigo-700" data-testid="watchlist-save-btn">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save watchlist"}</Button>
      </div>
    </form>
  );
}

export default function Watchlist() {
  const [list, setList] = useState([]);
  const [editing, setEditing] = useState(null);
  const load = () => api.get("/watchlists").then((r) => setList(r.data));
  useEffect(() => {
    load();
  }, []);

  const toggle = async (w) => {
    const body = { ...w, active: !w.active };
    delete body.id; delete body.user_id; delete body.created_at;
    await api.put(`/watchlists/${w.id}`, body);
    load();
  };
  const remove = async (w) => {
    await api.delete(`/watchlists/${w.id}`);
    toast.success("Watchlist deleted");
    load();
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10" data-testid="watchlist-page">
      <span className="overline-label">Smart alerts</span>
      <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 mt-1">Watchlist</h1>
      <p className="text-slate-600 mt-2">Get an in-app notification when a new report matches what you're looking for.</p>
      <div className="mt-6 grid lg:grid-cols-[1.2fr_1fr] gap-6 items-start">
        {editing ? <WatchForm key={editing.id} initial={editing} onSaved={() => { setEditing(null); load(); }} onCancel={() => setEditing(null)} /> : <WatchForm onSaved={load} />}
        <div className="space-y-3">
          {list.length === 0 ? <EmptyState icon={Eye} title="No watchlists yet" /> : list.map((w) => (
            <div key={w.id} className="card-surface p-4" data-testid={`watchlist-${w.id}`}>
              <div className="flex items-center justify-between gap-2">
                <div className="font-semibold text-slate-900">{w.name}</div>
                <Switch checked={w.active} onCheckedChange={() => toggle(w)} data-testid={`watchlist-toggle-${w.id}`} aria-label="Alerts on" />
              </div>
              <div className="text-xs text-slate-500 mt-1">
                {[w.keywords, CATEGORY_LABELS[w.category], w.color, w.locations?.join(", ")].filter(Boolean).join(" · ")} · {w.item_type} · ≥{w.threshold}%
              </div>
              {w.reference_image && <img src={fileUrl(w.reference_image)} alt="" className="mt-2 h-12 w-12 rounded object-cover" />}
              <div className="mt-2 flex gap-2">
                <Button size="sm" variant="outline" onClick={() => setEditing(w)} data-testid={`watchlist-edit-${w.id}`}><Pencil className="h-3.5 w-3.5 mr-1" />Edit</Button>
                <Button size="sm" variant="outline" className="text-red-600" onClick={() => remove(w)} data-testid={`watchlist-delete-${w.id}`}><Trash2 className="h-3.5 w-3.5 mr-1" />Delete</Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
