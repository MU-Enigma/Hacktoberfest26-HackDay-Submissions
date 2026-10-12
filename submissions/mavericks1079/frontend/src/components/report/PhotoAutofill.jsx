import { useEffect, useState } from "react";
import { Camera, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/constants";

export function PhotoAutofill({ path, onSuggest }) {
  const [s, setS] = useState(null);
  const [busy, setBusy] = useState(!!path);

  useEffect(() => {
    if (!path) return;
    api.post("/ml/photo-suggest", { path })
      .then((r) => {
        setS(r.data);
        onSuggest(r.data);
      })
      .catch(() => setS(null))
      .finally(() => setBusy(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path]);

  if (!path || (!busy && !s)) return null;
  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50/60 p-4 text-sm" data-testid="photo-autofill-card">
      <div className="flex items-center gap-2 font-semibold text-emerald-800">
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}Suggested from your photo
      </div>
      {s && (
        <div className="mt-2 space-y-1 text-slate-700">
          <div data-testid="photo-autofill-category">
            Category: {s.category ? <b>{CATEGORY_LABELS[s.category]} ({Math.round(s.confidence * 100)}%)</b> : <span className="text-slate-500">not confident enough to suggest — please choose</span>}
          </div>
          <div data-testid="photo-autofill-colors">Colour: {s.colors.length ? <b>{s.colors.join(", ")}</b> : <span className="text-slate-500">no clear colour</span>}</div>
          <div className="text-xs text-slate-500">Model saw: {s.image_labels.map((l) => l.label).join(", ")}. You can change anything below; typing a title also refines the category.</div>
        </div>
      )}
    </div>
  );
}
