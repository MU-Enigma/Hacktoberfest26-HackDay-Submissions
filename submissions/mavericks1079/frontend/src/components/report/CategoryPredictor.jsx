import { useEffect, useRef, useState } from "react";
import { Brain, Loader2, AlertTriangle } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/constants";

export function CategoryPredictor({ title, description, category, onPredict, onPick }) {
  const [pred, setPred] = useState(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef(null);

  useEffect(() => {
    if (title.trim().length < 3) return undefined;
    clearTimeout(timer.current);
    timer.current = setTimeout(async () => {
      setBusy(true);
      try {
        const { data } = await api.post("/ml/categorize", { title, description });
        setPred(data);
        onPredict(data);
      } finally {
        setBusy(false);
      }
    }, 600);
    return () => clearTimeout(timer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title, description]);

  if (!pred && !busy) return null;
  return (
    <div className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4" data-testid="ml-prediction-card">
      <div className="flex items-center gap-2 text-sm font-semibold text-indigo-800">
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Brain className="h-4 w-4" />}
        ML category suggestion
      </div>
      {pred && (
        <>
          <div className="mt-2 flex items-center justify-between text-sm">
            <span className="font-bold text-slate-900" data-testid="ml-predicted-category">{CATEGORY_LABELS[pred.model_top]}</span>
            <span className="font-mono text-indigo-700" data-testid="ml-confidence">{Math.round(pred.confidence * 100)}% confidence</span>
          </div>
          <Progress value={pred.confidence * 100} className="h-1.5 mt-2" />
          {pred.uncertain && (
            <p className="mt-2 text-xs text-amber-700 flex items-center gap-1" data-testid="ml-uncertain">
              <AlertTriangle className="h-3.5 w-3.5" />The model is unsure, so we defaulted to "Other". Please pick the right category.
            </p>
          )}
          <div className="mt-3 flex flex-wrap gap-1.5">
            {pred.top.map((t) => (
              <button type="button" key={t.category} onClick={() => onPick(t.category)} data-testid={`ml-option-${t.category}`}
                className={`text-xs rounded-full px-2.5 py-1 border transition-colors ${category === t.category ? "bg-indigo-600 text-white border-indigo-600" : "bg-white border-slate-200 text-slate-600 hover:border-indigo-300"}`}>
                {t.label} · {Math.round(t.probability * 100)}%
              </button>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-slate-500">{pred.model}</p>
        </>
      )}
    </div>
  );
}
