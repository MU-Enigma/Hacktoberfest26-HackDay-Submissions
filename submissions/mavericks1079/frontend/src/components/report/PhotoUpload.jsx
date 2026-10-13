import { useState } from "react";
import { ImagePlus, Loader2, X } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, fileUrl } from "@/lib/api";

export function PhotoUpload({ paths, onChange, max = 3, testId = "photo-upload" }) {
  const [busy, setBusy] = useState(false);

  const pick = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) return toast.error("Image must be 5 MB or smaller");
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/uploads", fd);
      onChange([...paths, data.path]);
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-wrap gap-3" data-testid={testId}>
      {paths.map((p) => (
        <div key={p} className="relative">
          <img src={fileUrl(p)} alt="Upload preview" className="h-24 w-24 rounded-xl object-cover border border-slate-200" />
          <button type="button" onClick={() => onChange(paths.filter((x) => x !== p))} className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-slate-900 text-white grid place-items-center" aria-label="Remove photo">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
      {paths.length < max && (
        <label className="h-24 w-24 rounded-xl border-2 border-dashed border-slate-300 hover:border-indigo-400 grid place-items-center cursor-pointer text-slate-400 hover:text-indigo-600 transition-colors">
          {busy ? <Loader2 className="h-5 w-5 animate-spin" /> : <div className="flex flex-col items-center text-xs gap-1"><ImagePlus className="h-5 w-5" />Add photo</div>}
          <input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={pick} disabled={busy} data-testid={`${testId}-input`} />
        </label>
      )}
    </div>
  );
}
