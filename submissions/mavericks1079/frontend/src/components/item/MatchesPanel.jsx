import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ThumbsUp, ThumbsDown, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ItemThumb } from "@/components/ItemCard";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";

const LABELS = { description: "Description", category: "Category", attributes: "Colour & attributes", location: "Location", date: "Date", image: "Photo similarity" };

export function MatchesPanel({ itemId }) {
  const [data, setData] = useState(null);
  const load = () => api.get(`/items/${itemId}/matches`).then((r) => setData(r.data)).catch(() => setData({ matches: [] }));
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itemId]);

  const feedback = async (id, relevant) => {
    await api.post(`/matches/${id}/feedback`, { relevant });
    load();
  };

  if (!data) return null;
  return (
    <section className="card-surface p-6" data-testid="matches-panel">
      <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2"><Sparkles className="h-5 w-5 text-indigo-600" />Potential matches</h2>
      <p className="text-xs text-slate-500 mt-1">Scores are suggestions only and never authorize a handover. Private clues are not used for matching. When both reports have photos, a pretrained image model (MobileNetV2) adds a photo-similarity signal — visual similarity is never proof of ownership.</p>
      {data.matches.length === 0 ? <p className="text-sm text-slate-500 mt-4" data-testid="no-matches">No matches yet. We'll notify you when one appears.</p> : (
        <div className="mt-4 space-y-4">
          {data.matches.map((m) => (
            <div key={m.id} className={`rounded-xl border p-4 ${m.feedback === "irrelevant" ? "opacity-50 border-slate-200" : "border-indigo-100"}`} data-testid={`match-${m.id}`}>
              <div className="flex gap-3 items-start">
                <ItemThumb item={m.item} className="h-16 w-16 rounded-lg shrink-0" />
                <div className="flex-1 min-w-0">
                  <Link to={`/items/${m.item.id}`} className="font-semibold text-slate-900 hover:text-indigo-700" data-testid={`match-link-${m.id}`}>{m.item.title}</Link>
                  <div className="text-xs text-slate-500">{m.item.location}</div>
                  <div className="mt-1"><StatusBadge status={m.item.status} /></div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-extrabold font-mono text-indigo-700" data-testid={`match-score-${m.id}`}>{m.score}</div>
                  <div className="text-[10px] uppercase text-slate-400 font-semibold">/ 100</div>
                </div>
              </div>
              <div className="mt-3 grid grid-cols-3 sm:grid-cols-6 gap-2">
                {Object.entries(m.breakdown).map(([k, v]) => (
                  <div key={k} title={`${LABELS[k]} (weight ${Math.round((m.weights?.[k] ?? 0) * 100)}%)`} data-testid={`match-${m.id}-factor-${k}`}>
                    <div className={`h-1.5 rounded-full bg-slate-100 overflow-hidden`}><div className={`h-full ${k === "image" ? "bg-emerald-500" : "bg-indigo-500"}`} style={{ width: `${v * 100}%` }} /></div>
                    <div className="text-[10px] text-slate-500 mt-1 truncate">{LABELS[k]} {Math.round(v * 100)}%</div>
                  </div>
                ))}
              </div>
              <ul className="mt-2 text-xs text-slate-600 list-disc pl-4" data-testid={`match-reasons-${m.id}`}>{m.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
              <div className="mt-3 flex gap-2">
                <Button size="sm" variant={m.feedback === "relevant" ? "default" : "outline"} onClick={() => feedback(m.id, true)} data-testid={`match-relevant-${m.id}`}><ThumbsUp className="h-3.5 w-3.5 mr-1" />Relevant</Button>
                <Button size="sm" variant={m.feedback === "irrelevant" ? "default" : "outline"} onClick={() => feedback(m.id, false)} data-testid={`match-irrelevant-${m.id}`}><ThumbsDown className="h-3.5 w-3.5 mr-1" />Not relevant</Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
