import { useEffect, useState } from "react";
import { Loader2, KeyRound } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, errMsg } from "@/lib/api";

export function ClaimDialog({ item, open, onOpenChange, onDone }) {
  const [f, setF] = useState({ marks: "", contents: "", circumstances: "", lost_item_id: "" });
  const [mine, setMine] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) api.get("/items/mine").then((r) => setMine(r.data.filter((i) => i.type === "lost" && !["RETURNED", "CLOSED"].includes(i.status))));
  }, [open]);

  const submit = async () => {
    setError("");
    if (f.marks.trim().length < 3 || f.circumstances.trim().length < 3) return setError("Please fill in the distinctive marks and how you lost it");
    setBusy(true);
    try {
      const { data } = await api.post(`/items/${item.id}/claims`, { ...f, lost_item_id: f.lost_item_id || null });
      toast.success(data.message);
      onOpenChange(false);
      onDone();
    } catch (e) {
      setError(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="claim-dialog" className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><KeyRound className="h-5 w-5 text-indigo-600" />Claim "{item.title}"</DialogTitle>
          <DialogDescription>Describe details only the true owner would know. Public info like name, category or colour is not enough. False claims violate the Responsible Use Policy.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-1.5"><Label htmlFor="c-marks">Distinctive marks, stickers, engravings</Label><Textarea id="c-marks" rows={2} value={f.marks} onChange={set("marks")} data-testid="claim-marks-input" /></div>
          <div className="space-y-1.5"><Label htmlFor="c-contents">Contents or accessories (optional)</Label><Textarea id="c-contents" rows={2} value={f.contents} onChange={set("contents")} data-testid="claim-contents-input" /></div>
          <div className="space-y-1.5"><Label htmlFor="c-circ">Where and when did you lose it?</Label><Textarea id="c-circ" rows={2} value={f.circumstances} onChange={set("circumstances")} data-testid="claim-circumstances-input" /></div>
          {mine.length > 0 && (
            <div className="space-y-1.5">
              <Label>Link to your lost report (optional)</Label>
              <Select value={f.lost_item_id || "none"} onValueChange={(v) => setF({ ...f, lost_item_id: v === "none" ? "" : v })}>
                <SelectTrigger data-testid="claim-lost-item-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Don't link</SelectItem>
                  {mine.map((i) => <SelectItem key={i.id} value={i.id}>{i.title}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          )}
          {error && <p className="text-sm text-red-600" data-testid="claim-error">{error}</p>}
          <p className="text-xs text-slate-500">You have up to 3 attempts per item per 24 hours. Correct answers are never revealed.</p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={submit} disabled={busy} className="bg-indigo-600 hover:bg-indigo-700" data-testid="claim-submit-btn">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Submit claim"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
