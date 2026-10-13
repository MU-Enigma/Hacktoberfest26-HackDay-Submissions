import { STATUS_STYLE } from "@/lib/constants";

export const StatusBadge = ({ status, testId }) => (
  <span data-testid={testId || "status-badge"} className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-bold tracking-wide whitespace-nowrap ${STATUS_STYLE[status] || STATUS_STYLE.CLOSED}`}>
    <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
    {status}
  </span>
);

export const TypePill = ({ type }) => (
  <span className={`rounded-md px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider ${type === "lost" ? "bg-amber-500 text-white" : "bg-emerald-600 text-white"}`}>
    {type}
  </span>
);
