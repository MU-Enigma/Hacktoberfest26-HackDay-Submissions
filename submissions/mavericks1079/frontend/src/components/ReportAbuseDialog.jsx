import { useState } from "react";
import { Flag } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { api, errMsg } from "@/lib/api";
import { ABUSE_REASONS } from "@/lib/constants";
import { useAuth } from "@/context/AuthContext";
import { useNavigate } from "react-router-dom";

export function ReportAbuseDialog({ targetType, targetId, label = "Report abuse", size = "sm" }) {
  const { user } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [details, setDetails] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    if (!reason) return toast.error("Choose a reason");
    setBusy(true);
    try {
      const { data } = await api.post("/moderation/reports", { target_type: targetType, target_id: targetId, reason, details });
      toast.success(`Report received (ref ${data.reference}). An administrator will review it.`);
      setOpen(false);
      setReason("");
      setDetails("");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Button variant="ghost" size={size} className="text-slate-500 hover:text-red-600" data-testid={`report-abuse-btn-${targetType}`}
        onClick={() => (user ? setOpen(true) : nav("/login"))}>
        <Flag className="h-4 w-4 mr-1.5" />{label}
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="report-abuse-dialog">
          <DialogHeader>
            <DialogTitle>Report misuse</DialogTitle>
            <DialogDescription>Reports are reviewed by administrators. Please do not include passwords or unnecessary personal data.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label>Reason</Label>
              <Select value={reason} onValueChange={setReason}>
                <SelectTrigger data-testid="abuse-reason-select"><SelectValue placeholder="Select a reason" /></SelectTrigger>
                <SelectContent>{ABUSE_REASONS.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="abuse-details">Details (optional)</Label>
              <Textarea id="abuse-details" value={details} onChange={(e) => setDetails(e.target.value)} data-testid="abuse-details-input" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={submit} disabled={busy} className="bg-red-600 hover:bg-red-700" data-testid="abuse-submit-btn">Submit report</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
