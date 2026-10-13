import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, CheckCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ItemCard";
import { Spinner } from "@/components/ProtectedRoute";
import { api, timeAgo } from "@/lib/api";

export default function Notifications() {
  const [data, setData] = useState(null);
  const nav = useNavigate();
  const load = () => api.get("/notifications").then((r) => setData(r.data));
  useEffect(() => {
    load();
  }, []);

  const open = async (n) => {
    if (!n.read) await api.post(`/notifications/${n.id}/read`);
    if (n.link) nav(n.link);
    else load();
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10" data-testid="notifications-page">
      <div className="flex items-end justify-between">
        <div>
          <span className="overline-label">Inbox</span>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 mt-1">Notifications</h1>
        </div>
        <Button variant="outline" onClick={async () => { await api.post("/notifications/read-all"); load(); }} data-testid="notifications-read-all"><CheckCheck className="h-4 w-4 mr-2" />Mark all read</Button>
      </div>
      <div className="mt-6 space-y-2">
        {!data ? <Spinner /> : data.items.length === 0 ? <EmptyState icon={Bell} title="No notifications yet" text="Match alerts, watchlist hits and claim updates appear here." /> : data.items.map((n) => (
          <button key={n.id} onClick={() => open(n)} data-testid={`notification-${n.id}`}
            className={`w-full text-left card-surface p-4 flex gap-3 hover:shadow-md transition-shadow ${n.read ? "opacity-70" : "border-indigo-200 bg-indigo-50/40"}`}>
            <span className={`mt-1.5 h-2 w-2 rounded-full shrink-0 ${n.read ? "bg-slate-300" : "bg-indigo-600"}`} />
            <div className="min-w-0 flex-1">
              <div className="flex justify-between gap-2"><span className="font-semibold text-slate-900">{n.title}</span><span className="text-xs text-slate-400 shrink-0">{timeAgo(n.created_at)}</span></div>
              <p className="text-sm text-slate-600 mt-0.5">{n.body}</p>
              <span className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">{n.type}{n.read ? "" : " · unread"}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
