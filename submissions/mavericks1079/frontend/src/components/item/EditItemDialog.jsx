import { useState } from "react";
import { Pencil } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, errMsg } from "@/lib/api";

export function EditItemDialog({ item, onSaved }) {
  const [open, setOpen] = useState(false);
  const found = item.type === "found";
  const [f, setF] = useState({ description: item.description, color: item.color || "", attributes: item.attributes || "", private_clues: item.private_clues || "",
    secure_collection_location: item.secure_collection_location || "", collection_window: item.collection_window || "", holder: item.holder || "office" });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const save = async () => {
    const body = found ? f : { description: f.description, color: f.color, attributes: f.attributes, private_clues: f.private_clues };
    try {
      await api.patch(`/items/${item.id}`, body);
      toast.success("Report updated. Matches recalculated.");
      setOpen(false);
      onSaved();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  return (
    <>
      <Button variant="outline" size="sm" onClick={() => setOpen(true)} data-testid="item-edit-btn"><Pencil className="h-4 w-4 mr-1.5" />Edit</Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="edit-item-dialog" className="max-w-lg">
          <DialogHeader><DialogTitle>Update report</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5"><Label htmlFor="e-desc">Description</Label><Textarea id="e-desc" value={f.description} onChange={set("description")} data-testid="edit-description-input" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5"><Label htmlFor="e-color">Colour</Label><Input id="e-color" value={f.color} onChange={set("color")} /></div>
              <div className="space-y-1.5"><Label htmlFor="e-attr">Attributes</Label><Input id="e-attr" value={f.attributes} onChange={set("attributes")} /></div>
            </div>
            <div className="space-y-1.5"><Label htmlFor="e-clues">Private clues</Label><Textarea id="e-clues" rows={2} value={f.private_clues} onChange={set("private_clues")} data-testid="edit-clues-input" /></div>
            {found && (
              <>
                <div className="space-y-1.5"><Label htmlFor="e-secure">Storage / collection location (private)</Label><Input id="e-secure" value={f.secure_collection_location} onChange={set("secure_collection_location")} data-testid="edit-secure-location-input" /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5"><Label htmlFor="e-window">Collection window</Label><Input id="e-window" value={f.collection_window} onChange={set("collection_window")} data-testid="edit-window-input" /></div>
                  <div className="space-y-1.5">
                    <Label>Item is with</Label>
                    <Select value={f.holder} onValueChange={(v) => setF({ ...f, holder: v })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent><SelectItem value="office">Campus office</SelectItem><SelectItem value="finder">Me (finder)</SelectItem></SelectContent>
                    </Select>
                  </div>
                </div>
              </>
            )}
          </div>
          <DialogFooter><Button onClick={save} className="bg-indigo-600 hover:bg-indigo-700" data-testid="edit-save-btn">Save changes</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
