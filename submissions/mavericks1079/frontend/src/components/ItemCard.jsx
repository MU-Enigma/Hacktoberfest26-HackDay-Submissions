import { Link } from "react-router-dom";
import { MapPin, Clock, ImageOff } from "lucide-react";
import { StatusBadge, TypePill } from "@/components/StatusBadge";
import { CATEGORY_LABELS } from "@/lib/constants";
import { fileUrl, timeAgo } from "@/lib/api";

export const ItemThumb = ({ item, className = "" }) => {
  const src = fileUrl(item.image_paths?.[0]);
  return src ? (
    <img src={src} alt={item.title} loading="lazy" className={`object-cover ${className}`} />
  ) : (
    <div className={`grid place-items-center bg-slate-100 text-slate-400 ${className}`}><ImageOff className="h-6 w-6" /></div>
  );
};

export function ItemCard({ item, extra }) {
  return (
    <Link to={`/items/${item.id}`} data-testid={`item-card-${item.id}`} className="group card-surface overflow-hidden flex flex-col hover:shadow-md hover:-translate-y-0.5 transition-[transform,box-shadow] duration-200">
      <div className="relative">
        <ItemThumb item={item} className="h-44 w-full group-hover:scale-[1.02] transition-transform duration-300" />
        <div className="absolute top-3 left-3"><TypePill type={item.type} /></div>
      </div>
      <div className="p-4 flex flex-col gap-2 flex-1">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-semibold text-slate-900 leading-snug line-clamp-2">{item.title}</h3>
        </div>
        <div className="text-xs text-indigo-600 font-semibold">{CATEGORY_LABELS[item.category] || item.category}</div>
        <div className="flex flex-col gap-1 text-xs text-slate-500 mt-auto">
          <span className="flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{item.location}</span>
          <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" />Reported {timeAgo(item.created_at)}</span>
        </div>
        <div className="pt-1 flex items-center justify-between gap-2">
          <StatusBadge status={item.status} />
          {extra}
        </div>
      </div>
    </Link>
  );
}

export const EmptyState = ({ icon: Icon, title, text, action, testId = "empty-state" }) => (
  <div data-testid={testId} className="card-surface border-dashed p-10 text-center flex flex-col items-center gap-3">
    {Icon && <Icon className="h-10 w-10 text-slate-300" />}
    <div className="font-semibold text-slate-800">{title}</div>
    {text && <p className="text-sm text-slate-500 max-w-md">{text}</p>}
    {action}
  </div>
);
