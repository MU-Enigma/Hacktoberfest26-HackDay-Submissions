export const CATEGORY_LABELS = {
  electronics: "Electronics",
  id_cards: "ID cards & access cards",
  wallets: "Wallets & purses",
  keys: "Keys",
  bags: "Bags & backpacks",
  books: "Books & stationery",
  clothing: "Clothing & accessories",
  bottles: "Bottles & containers",
  jewelry: "Jewelry",
  other: "Other",
};

export const STATUSES = ["LOST", "FOUND", "MATCH FOUND", "CLAIM PENDING", "VERIFICATION IN PROGRESS", "READY FOR HANDOVER", "RETURNED", "CLOSED"];

export const STATUS_STYLE = {
  LOST: "bg-amber-100 text-amber-800 border-amber-200",
  FOUND: "bg-emerald-100 text-emerald-800 border-emerald-200",
  "MATCH FOUND": "bg-indigo-100 text-indigo-800 border-indigo-200",
  "CLAIM PENDING": "bg-blue-100 text-blue-800 border-blue-200",
  "VERIFICATION IN PROGRESS": "bg-purple-100 text-purple-800 border-purple-200",
  "READY FOR HANDOVER": "bg-teal-100 text-teal-800 border-teal-200",
  RETURNED: "bg-green-100 text-green-800 border-green-200",
  CLOSED: "bg-slate-100 text-slate-600 border-slate-200",
};

export const CLAIM_STYLE = {
  pending: "bg-blue-100 text-blue-800",
  verifying: "bg-purple-100 text-purple-800",
  approved: "bg-teal-100 text-teal-800",
  completed: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-700",
  cancelled: "bg-slate-100 text-slate-600",
};

export const ABUSE_REASONS = ["Fake or prank report", "False ownership claim", "Suspected theft or withholding", "Harassment or threats", "Impersonation", "Misleading evidence", "Other"];
