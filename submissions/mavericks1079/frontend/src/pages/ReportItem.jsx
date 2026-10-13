import { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { Loader2, Eye, ArrowLeft, Lock, PackageSearch, HandHeart } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CategoryPredictor } from "@/components/report/CategoryPredictor";
import { PhotoUpload } from "@/components/report/PhotoUpload";
import { DuplicateDialog } from "@/components/report/DuplicateDialog";
import { PolicyAckDialog } from "@/components/report/PolicyAckDialog";
import { PhotoAutofill } from "@/components/report/PhotoAutofill";
import { useLocations } from "@/pages/Browse";
import { api, errMsg, fileUrl, fmtDate } from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/constants";

const localNow = () => {
  const d = new Date();
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
  return d.toISOString().slice(0, 16);
};

const Field = ({ label, children, hint, htmlFor }) => (
  <div className="space-y-1.5">
    <Label htmlFor={htmlFor}>{label}</Label>
    {children}
    {hint && <p className="text-xs text-slate-500">{hint}</p>}
  </div>
);

const SelectField = ({ value, onChange, options, placeholder, testId }) => (
  <Select value={value} onValueChange={onChange}>
    <SelectTrigger data-testid={testId}><SelectValue placeholder={placeholder} /></SelectTrigger>
    <SelectContent>{options.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
  </Select>
);

export default function ReportItem({ mode }) {
  const lost = mode === "lost";
  const nav = useNavigate();
  const snapped = useLocation().state?.image_paths || [];
  const locs = useLocations();
  const [f, setF] = useState({ title: "", description: "", category: "", color: "", attributes: "", location: "", occurred_at: localNow(), private_clues: "",
    reward: "", contact_pref: "in_app", collection_pref: "", secure_collection_location: "", collection_window: "", holder: "office", notes_for_owner: "", image_paths: snapped });
  const [pred, setPred] = useState(null);
  const [touched, setTouched] = useState(false);
  const [photoCat, setPhotoCat] = useState(null);
  const [step, setStep] = useState("form");
  const [errors, setErrors] = useState({});
  const [dups, setDups] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e?.target ? e.target.value : e });

  const validate = () => {
    const e = {};
    if (f.title.trim().length < 2) e.title = "Enter an item name";
    if (f.description.trim().length < 5) e.description = "Add a short description (5+ characters)";
    if (!f.category) e.category = "Choose a category";
    if (!f.location) e.location = "Choose a location";
    if (!f.occurred_at) e.occurred_at = "Choose a date and time";
    if (!lost && f.image_paths.length === 0) e.image_paths = "A photo helps the owner recognise the item";
    if (!lost && !f.secure_collection_location.trim()) e.secure_collection_location = "Where can the owner collect it safely?";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const payload = () => ({ ...f, type: mode, occurred_at: new Date(f.occurred_at).toISOString(),
    predicted_category: pred?.category ?? null, prediction_confidence: pred?.confidence ?? null });

  const create = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/items", payload());
      toast.success("Report submitted. We'll alert you about matches.");
      nav(`/items/${data.id}`);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    setBusy(true);
    try {
      const p = payload();
      const { data } = await api.post("/items/check-duplicates", { type: mode, title: p.title, description: p.description, category: p.category, color: p.color, attributes: p.attributes, location: p.location, occurred_at: p.occurred_at, image_paths: p.image_paths });
      if (data.length) {
        setDups(data);
        setBusy(false);
        return;
      }
    } catch {
      /* duplicate check is advisory */
    }
    await create();
  };

  const Err = ({ k }) => (errors[k] ? <p className="text-xs text-red-600" data-testid={`error-${k}`}>{errors[k]}</p> : null);
  const Icon = lost ? PackageSearch : HandHeart;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10" data-testid={`report-${mode}-page`}>
      <PolicyAckDialog />
      <span className={`overline-label ${lost ? "!text-amber-600" : "!text-emerald-600"}`}>{lost ? "I lost it" : "I found it"}</span>
      <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 mt-1 flex items-center gap-3"><Icon className="h-8 w-8" />{lost ? "Report a lost item" : "Report a found item"}</h1>
      <p className="text-slate-600 mt-2">Takes about a minute. Report honestly — <Link to="/policy" className="text-indigo-600 underline">Responsible Use Policy</Link>.</p>
      {snapped.length > 0 && <p className="mt-2 text-sm text-emerald-700" data-testid="snap-photo-attached">Your photo search image is attached below.</p>}

      {step === "form" ? (
        <div className="card-surface p-6 sm:p-8 mt-6 space-y-5">
          <PhotoAutofill path={snapped[0]} onSuggest={(s) => {
            setPhotoCat(s.category);
            setF((st) => ({ ...st, category: st.category || s.category || "", color: st.color || s.colors.join(", ") }));
          }} />
          <Field label="Item name" htmlFor="title"><Input id="title" value={f.title} onChange={set("title")} placeholder={lost ? "e.g. Black Jansport backpack" : "e.g. Silver keys with red tag"} data-testid="report-title-input" /><Err k="title" /></Field>
          <Field label={lost ? "Detailed description" : "Honest description of visible characteristics"} htmlFor="desc">
            <Textarea id="desc" rows={3} value={f.description} onChange={set("description")} data-testid="report-description-input" /><Err k="description" />
          </Field>
          <CategoryPredictor title={f.title} description={f.description} category={f.category}
            onPredict={(p) => !touched && !(p.uncertain && photoCat) && setF((s) => ({ ...s, category: p.category }))} onPick={(c) => { setTouched(true); setF((s) => ({ ...s, category: c })); }} />
          <div className="grid sm:grid-cols-2 gap-4">
            <Field label="Category"><SelectField value={f.category} onChange={(v) => { setTouched(true); set("category")(v); }} options={Object.entries(CATEGORY_LABELS)} placeholder="Select category" testId="report-category-select" /><Err k="category" /></Field>
            <Field label="Colour" htmlFor="color"><Input id="color" value={f.color} onChange={set("color")} placeholder="e.g. black, red" data-testid="report-color-input" /></Field>
            <Field label={lost ? "Last-seen location" : "Where you found it"}><SelectField value={f.location} onChange={set("location")} options={locs.map((l) => [l.name, l.name])} placeholder="Select location" testId="report-location-select" /><Err k="location" /></Field>
            <Field label={lost ? "Approx. date & time lost" : "Date & time found"} htmlFor="when"><Input id="when" type="datetime-local" value={f.occurred_at} onChange={set("occurred_at")} data-testid="report-datetime-input" /><Err k="occurred_at" /></Field>
          </div>
          <Field label="Identifying characteristics (public)" htmlFor="attrs" hint="Brand, size, visible marks that are fine to show publicly."><Input id="attrs" value={f.attributes} onChange={set("attributes")} data-testid="report-attributes-input" /></Field>
          <Field label={lost ? "Photo (optional)" : "Item photograph"}><PhotoUpload paths={f.image_paths} onChange={set("image_paths")} /><Err k="image_paths" /></Field>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-2">
            <Label htmlFor="clues" className="flex items-center gap-2"><Lock className="h-4 w-4 text-indigo-600" />Private ownership clues {lost ? "(optional)" : "(recommended)"}</Label>
            <Textarea id="clues" rows={2} value={f.private_clues} onChange={set("private_clues")} placeholder={lost ? "e.g. engraving, sticker inside, contents" : "Hidden details only the true owner would know (contents, engravings, stickers)"} data-testid="report-private-clues-input" />
            <p className="text-xs text-slate-500">Never shown publicly, in search, feeds or notifications. {lost ? "" : "Used to verify claimants without revealing the answer."}</p>
          </div>
          {lost ? (
            <div className="grid sm:grid-cols-3 gap-4">
              <Field label="Reward (optional)" htmlFor="reward" hint="Subject to campus policy"><Input id="reward" value={f.reward} onChange={set("reward")} data-testid="report-reward-input" /></Field>
              <Field label="Contact preference"><SelectField value={f.contact_pref} onChange={set("contact_pref")} options={[["in_app", "In-app only"], ["campus_office", "Via campus office"]]} testId="report-contact-select" /></Field>
              <Field label="Collection preference" htmlFor="cpref"><Input id="cpref" value={f.collection_pref} onChange={set("collection_pref")} placeholder="e.g. Security Office" data-testid="report-collection-pref-input" /></Field>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Item is currently with"><SelectField value={f.holder} onChange={set("holder")} options={[["office", "An authorized campus office"], ["finder", "Me (the finder)"]]} testId="report-holder-select" /></Field>
              <Field label="Expected collection window" htmlFor="window"><Input id="window" value={f.collection_window} onChange={set("collection_window")} placeholder="e.g. Weekdays 10-17" data-testid="report-collection-window-input" /></Field>
              <Field label="Secure collection location (private)" htmlFor="secure" hint="Only shown to the approved claimant."><Input id="secure" value={f.secure_collection_location} onChange={set("secure_collection_location")} placeholder="e.g. Infra Office, front desk" data-testid="report-secure-location-input" /><Err k="secure_collection_location" /></Field>
              <Field label="Notes for the owner (optional)" htmlFor="notes"><Input id="notes" value={f.notes_for_owner} onChange={set("notes_for_owner")} data-testid="report-notes-input" /></Field>
            </div>
          )}
          <div className="flex justify-end"><Button onClick={() => validate() && setStep("preview")} className="rounded-full px-6 bg-indigo-600 hover:bg-indigo-700" data-testid="report-preview-btn"><Eye className="h-4 w-4 mr-2" />Preview report</Button></div>
        </div>
      ) : (
        <div className="card-surface p-6 sm:p-8 mt-6" data-testid="report-preview">
          <h2 className="text-lg font-bold text-slate-900">Preview & confirm</h2>
          <div className="mt-4 flex gap-4 flex-col sm:flex-row">
            {f.image_paths[0] && <img src={fileUrl(f.image_paths[0])} alt="" className="h-36 w-36 rounded-xl object-cover" />}
            <dl className="grid grid-cols-[130px_1fr] gap-x-3 gap-y-1.5 text-sm">
              {[["Item", f.title], ["Category", CATEGORY_LABELS[f.category]], ["Description", f.description], ["Colour", f.color || "-"], ["Location", f.location],
                ["When", fmtDate(f.occurred_at)], ["Private clues", f.private_clues ? "Stored privately" : "None"],
                ...(lost ? [["Reward", f.reward || "-"]] : [["Collection", f.secure_collection_location], ["Window", f.collection_window || "-"]])].map(([k, v]) => (
                <div key={k} className="contents"><dt className="text-slate-500">{k}</dt><dd className="text-slate-900 font-medium break-words">{v}</dd></div>
              ))}
            </dl>
          </div>
          <div className="mt-6 flex justify-between">
            <Button variant="outline" onClick={() => setStep("form")} data-testid="report-edit-btn"><ArrowLeft className="h-4 w-4 mr-2" />Edit</Button>
            <Button onClick={submit} disabled={busy} className="rounded-full px-6 bg-indigo-600 hover:bg-indigo-700" data-testid="report-submit-btn">
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : "Confirm & submit"}
            </Button>
          </div>
        </div>
      )}
      <DuplicateDialog dups={dups} busy={busy} onCancel={() => setDups(null)} onContinue={() => { setDups(null); create(); }} />
    </div>
  );
}
