import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { PolicyContent } from "@/components/PolicyContent";
import { useAuth } from "@/context/AuthContext";
import { api, errMsg } from "@/lib/api";
import { toast } from "sonner";

export function PolicyAckDialog() {
  const { user, refresh } = useAuth();
  const nav = useNavigate();
  const [ok, setOk] = useState(false);
  const open = !!user && !user.report_policy_ack;

  const accept = async () => {
    try {
      await api.post("/policy/report-ack");
      await refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && nav("/")}>
      <DialogContent data-testid="policy-ack-dialog" className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Before your first report</DialogTitle>
          <DialogDescription>Please review the Responsible Use Policy once more.</DialogDescription>
        </DialogHeader>
        <ScrollArea className="h-72 rounded-xl border border-slate-200 bg-slate-50 p-4"><PolicyContent compact /></ScrollArea>
        <label className="flex items-center gap-3 text-sm cursor-pointer">
          <Checkbox checked={ok} onCheckedChange={(v) => setOk(!!v)} data-testid="policy-ack-checkbox" />
          I will report honestly and respect other people's property.
        </label>
        <DialogFooter>
          <Button variant="outline" onClick={() => nav("/")}>Not now</Button>
          <Button disabled={!ok} onClick={accept} className="bg-indigo-600 hover:bg-indigo-700" data-testid="policy-ack-accept-btn">I agree, continue</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
