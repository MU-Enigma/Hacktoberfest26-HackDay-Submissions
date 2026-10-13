import { Link } from "react-router-dom";
import { PolicyContent } from "@/components/PolicyContent";

const REVIEW_NOTE = "This page is a hackathon draft. Its language requires university and legal review before production use. Back2U is not officially affiliated with or approved by any university.";

const PAGES = {
  about: {
    title: "About Back2U",
    sections: [
      ["Why Back2U exists", "Every semester students lose ID cards, keys, earphones, bottles and wallets. Notice boards and group chats are noisy and unsafe. Back2U gives a campus one trustworthy place to report, match and return belongings."],
      ["Built for the university community", "Fewer duplicate reports, faster recoveries, verified ownership and an auditable handover trail help students, campus security and administrators alike."],
      ["Our principle", "The rightful owner comes first. Every feature is designed to return items safely, never to let someone gain possession of another person's property."],
    ],
  },
  "how-it-works": {
    title: "How Back2U works",
    sections: [
      ["1. Report", "Tap I LOST IT or I FOUND IT. Our ML model suggests a category from your description, and you can correct it. Similar existing reports are flagged so you can avoid duplicates."],
      ["2. Match", "The matching engine compares lost and found reports using description similarity (35%), category (20%), colour and attributes (15%), location (15%) and date (15%). Each match shows a 0-100 score and an explanation."],
      ["3. Claim", "The owner submits a claim with independent identifying details. These are compared against private clues the finder stored, which are never shown publicly or revealed after a wrong attempt."],
      ["4. Verify", "The finder (or an administrator) reviews the claim and approves or rejects it. A high match score alone never approves a claim."],
      ["5. Secure handover", "The finder generates a single-use, short-lived QR code. The owner scans it (or enters a 6-digit code) on meeting, and the finder confirms. Only when both confirm is the item marked RETURNED and a receipt issued."],
    ],
  },
  safety: {
    title: "Safety guidelines",
    sections: [
      ["Meet in safe places", "Use staffed, public campus locations such as the Library front desk, the Infra Office or the Health Care Centre. Avoid isolated spots and late hours."],
      ["Verify ownership", "Ask for details that only the owner would know. Do not hand over an item just because someone knows its name or colour."],
      ["High-value items", "For phones, laptops, ID cards, wallets and jewellery we recommend handing the item to a campus office and verifying there."],
      ["Protect your privacy", "Keep conversations in Back2U. Never share passwords, OTPs or bank details. Report anyone who pressures you."],
    ],
  },
  privacy: {
    title: "Privacy policy",
    sections: [
      ["What we collect", "Account details (name, email, hashed password), your reports, photos, private clues, claims, watchlists, notifications, and an audit log of key actions."],
      ["Why", "To match reports, verify ownership, run secure handovers, prevent misuse and produce aggregate community statistics."],
      ["Who can access it", "Public listings show only item title, category, description, colour, general location and status. Private clues and storage locations are visible only to the report owner, approved claimants (storage location) and administrators."],
      ["Retention", "Reports and audit records are kept for the life of the deployment unless an administrator removes them. Retention periods must be defined by the deploying institution."],
      ["Assistance", "Use Report Misuse or contact your campus administrator to request help with your data."],
    ],
  },
  terms: {
    title: "Terms of service",
    sections: [
      ["Appropriate use", "Back2U is only for genuine lost-and-found recovery. All users must follow the Responsible Use Policy."],
      ["Your responsibilities", "Provide truthful information, keep found items safe, cooperate with verification and complete handovers in good faith."],
      ["Moderation", "Administrators review reports of misuse and automated flags. Decisions are made by humans and recorded with reasons."],
      ["Suspension and bans", "Accounts may be suspended for a period or permanently banned. Restricted accounts cannot report, claim or hand over items. You may appeal from your profile."],
    ],
  },
  help: {
    title: "Help & FAQs",
    sections: [
      ["How do I report an item?", "Click I LOST IT or I FOUND IT on the homepage, fill in the short form, preview and submit."],
      ["How do matches work?", "Open one of your reports to see ranked matches with scores and reasons. Mark them relevant or irrelevant to improve your list."],
      ["How do I claim an item?", "Open a found item and click 'This is mine'. Describe identifying details the finder can check. You have 3 attempts per item per day."],
      ["How does the QR handover work?", "After approval, open the handover page. The finder shows a QR code; the owner scans it or types the 6-digit code; the finder confirms. Both confirmations are required."],
      ["Something went wrong?", "Use Report Misuse for disputes or abuse. Do not share passwords or authentication codes in reports."],
    ],
  },
  notfound: { title: "Page not found", sections: [["", "The page you are looking for does not exist."]] },
};

export default function InfoPage({ slug }) {
  const page = PAGES[slug];
  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12" data-testid={`info-page-${slug}`}>
      <span className="overline-label">Back2U</span>
      <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 mt-1">{slug === "policy" ? "Responsible Use Policy" : page.title}</h1>
      <div className="card-surface p-6 sm:p-8 mt-6 space-y-6">
        {slug === "policy" ? <PolicyContent /> : page.sections.map(([h, t]) => (
          <div key={h || t}>
            {h && <h2 className="text-lg font-semibold text-slate-900">{h}</h2>}
            <p className="text-slate-600 leading-relaxed mt-1">{t}</p>
          </div>
        ))}
      </div>
      {slug !== "notfound" && <p className="text-xs text-slate-400 mt-4" data-testid="review-note">{REVIEW_NOTE}</p>}
      <div className="mt-6 flex flex-wrap gap-4 text-sm">
        <Link to="/" className="text-indigo-600 font-semibold">Back to home</Link>
        <Link to="/report-misuse" className="text-indigo-600 font-semibold">Report misuse</Link>
      </div>
    </div>
  );
}
