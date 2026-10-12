import { Navigate, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export const Spinner = ({ label = "Loading..." }) => (
  <div data-testid="loading-spinner" className="flex items-center justify-center gap-2 py-24 text-slate-500">
    <Loader2 className="h-5 w-5 animate-spin" /> {label}
  </div>
);

export function ProtectedRoute({ children, admin }) {
  const { user } = useAuth();
  const loc = useLocation();
  if (user === null) return <Spinner />;
  if (!user) return <Navigate to={`/login?next=${encodeURIComponent(loc.pathname + loc.search)}`} replace />;
  if (admin && user.role !== "admin") return <Navigate to="/" replace />;
  return children;
}
