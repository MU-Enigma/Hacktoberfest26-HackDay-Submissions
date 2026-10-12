import { Link } from "react-router-dom";
import { Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { ItemThumb } from "@/components/ItemCard";

export function DuplicateDialog({ dups, onContinue, onCancel, busy }) {
  const first = dups?.[0];
  return (
    <Dialog open={!!dups?.length} onOpenChange={(o) => !o && onCancel()}>
      <DialogContent data-testid="duplicate-dialog" className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Copy className="h-5 w-5 text-amber-600" />Possible duplicate report</DialogTitle>
          <DialogDescription>
            An item similar to this has already been reported near {first?.location}. Would you like to review the existing report?
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          {dups?.map((d) => (
            <Link key={d.id} to={`/items/${d.id}`} target="_blank" className="flex gap-3 items-center rounded-xl border border-slate-200 p-3 hover:bg-slate-50" data-testid={`duplicate-view-${d.id}`}>
              <ItemThumb item={d} className="h-12 w-12 rounded-lg" />
              <div className="min-w-0 flex-1">
                <div className="font-semibold text-sm truncate">{d.title}</div>
                <div className="text-xs text-slate-500">{d.location} · {d.reasons.slice(0, 2).join(", ")}</div>
              </div>
              <span className="font-mono text-sm font-bold text-amber-700">{d.similarity}%</span>
            </Link>
          ))}
        </div>
        <p className="text-xs text-slate-500">Multiple genuine reports can describe the same incident. Nothing is deleted automatically.</p>
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onCancel} data-testid="duplicate-cancel-btn">Cancel submission</Button>
          <Button asChild variant="secondary" data-testid="duplicate-view-btn"><Link to={`/items/${first?.id}`} target="_blank">View similar report</Link></Button>
          <Button onClick={onContinue} disabled={busy} className="bg-indigo-600 hover:bg-indigo-700" data-testid="duplicate-continue-btn">Continue creating new report</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
