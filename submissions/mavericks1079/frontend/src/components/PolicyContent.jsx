export const POLICY_RULES = [
  "Using Back2U for fun, pranks, fake reports, harassment, or any purpose unrelated to genuine lost-and-found recovery.",
  "Falsely claiming ownership of an item that does not belong to you.",
  "Attempting to deceive a finder, student, administrator, or rightful owner to obtain possession of someone else's property.",
  "Knowingly withholding, concealing, misappropriating, or attempting to steal an item that you have found.",
  "Uploading fake, misleading, manipulated, or fraudulent reports or evidence.",
  "Attempting to bypass ownership verification, manipulate QR handovers, exploit security vulnerabilities, or gain unauthorized access to another user's information.",
  "Abusing the platform to impersonate students, threaten users, or interfere with legitimate recovery requests.",
];

export function PolicyContent({ compact }) {
  return (
    <div data-testid="policy-content" className={`text-slate-700 leading-relaxed space-y-4 ${compact ? "text-sm" : "text-base"}`}>
      <p className="font-bold text-slate-900">Use Back2U responsibly. Help return belongings, never misuse them.</p>
      <p>Back2U is exclusively intended to help students report lost belongings, report found items, and return property to its rightful owner.</p>
      <div>
        <p className="font-semibold text-slate-900 mb-2">The following activities are strictly prohibited:</p>
        <ol className="list-decimal pl-5 space-y-1.5">
          {POLICY_RULES.map((r) => <li key={r}>{r}</li>)}
        </ol>
      </div>
      <div>
        <p className="font-semibold text-slate-900 mb-2">Consequences of misuse</p>
        <p>Any user found engaging in these prohibited activities may have their account suspended or permanently banned from Back2U. Where credible evidence of serious or repeated misconduct exists, the Back2U administration may report the incident to the relevant university authorities in accordance with applicable university policies and procedures.</p>
        <p className="mt-2">Such reports may result in disciplinary action by the university, depending on the nature of the incident and the university's applicable rules.</p>
        <p className="mt-2">Serious suspected theft, fraud, or other potentially unlawful conduct may also be referred to the appropriate authorities where warranted.</p>
      </div>
      <p>By registering and using Back2U, users acknowledge that they are expected to provide truthful information, respect other students' property, cooperate with legitimate ownership verification, and use the platform exclusively for genuine recovery purposes.</p>
      <p className="text-xs text-slate-500">Policy version 1.0. Moderation decisions are made by human administrators; automated flags only identify cases for review. Disputed decisions can be appealed from your profile.</p>
    </div>
  );
}
