import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Camera, Loader2, X, ScanSearch, PackageSearch, HandHeart } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ItemCard } from "@/components/ItemCard";
import { useAuth } from "@/context/AuthContext";
import { api, errMsg } from "@/lib/api";

export function PhotoSearchButton({ type, onResults, busy, setBusy }) {
  const { user } = useAuth();
  const nav = useNavigate();
  const input = useRef(null);

  const pick = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) return toast.error("Image must be 5 MB or smaller");
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/items/photo-search", fd, { params: type ? { type } : {} });
      onResults({ ...data, file, preview: URL.createObjectURL(file) });
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Button type="button" variant="outline" disabled={busy} className="h-11 bg-white" data-testid="photo-search-btn"
        onClick={() => (user ? input.current?.click() : nav("/login?next=/browse"))}>
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
        <span className="ml-2 hidden sm:inline">Search by photo</span>
      </Button>
      <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={pick} data-testid="photo-search-input" />
    </>
  );
}

function SnapToReport({ file, empty }) {
  const nav = useNavigate();
  const [busy, setBusy] = useState("");
  const start = async (mode) => {
    setBusy(mode);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/uploads", fd);
      nav(`/report/${mode}`, { state: { image_paths: [data.path] } });
    } catch (err) {
      toast.error(errMsg(err));
      setBusy("");
    }
  };
  return (
    <div className="mt-4 rounded-xl bg-slate-50 border border-slate-200 p-4" data-testid="snap-to-report">
      <p className="text-sm text-slate-600" data-testid={empty ? "photo-search-empty" : "snap-not-found-text"}>
        {empty ? "No visually similar items found. Start a report with this photo attached:" : "Not what you're looking for? Start a report with this photo attached:"}
      </p>
      <div className="mt-3 flex flex-col sm:flex-row gap-2">
        <Button onClick={() => start("lost")} disabled={!!busy} className="rounded-full bg-amber-500 hover:bg-amber-600" data-testid="snap-report-lost-btn">
          {busy === "lost" ? <Loader2 className="h-4 w-4 animate-spin" /> : <PackageSearch className="h-4 w-4 mr-2" />}I lost this
        </Button>
        <Button onClick={() => start("found")} disabled={!!busy} className="rounded-full bg-emerald-600 hover:bg-emerald-700" data-testid="snap-report-found-btn">
          {busy === "found" ? <Loader2 className="h-4 w-4 animate-spin" /> : <HandHeart className="h-4 w-4 mr-2" />}I found this
        </Button>
      </div>
      <p className="text-xs text-slate-400 mt-2">The photo is only saved if you choose one of these options.</p>
    </div>
  );
}

export function PhotoSearchResults({ data, onClear }) {
  return (
    <section className="mt-6 card-surface p-5 border-emerald-200" data-testid="photo-search-results">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <img src={data.preview} alt="Your search" className="h-14 w-14 rounded-lg object-cover border border-slate-200" />
          <div>
            <h2 className="font-bold text-slate-900 flex items-center gap-2"><ScanSearch className="h-4 w-4 text-emerald-600" />Visually similar items</h2>
            <p className="text-xs text-slate-500">{data.results.length} of {data.searched} photographed reports look similar. Your photo is not saved. Looking alike is never proof of ownership.</p>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={onClear} data-testid="photo-search-clear"><X className="h-4 w-4 mr-1" />Clear</Button>
      </div>
      {data.results.length > 0 && (
        <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {data.results.map((i) => (
            <ItemCard key={i.id} item={i} extra={<span className="font-mono text-xs font-bold text-emerald-700 bg-emerald-50 rounded px-1.5 py-0.5" data-testid={`photo-similarity-${i.id}`}>{i.photo_similarity}% alike</span>} />
          ))}
        </div>
      )}
      <SnapToReport file={data.file} empty={data.results.length === 0} />
    </section>
  );
}
