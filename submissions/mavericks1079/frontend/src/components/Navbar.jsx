import { useEffect, useState } from "react";
import { Link, NavLink, useNavigate, useLocation } from "react-router-dom";
import { Bell, Menu, X, User, LogOut, Shield, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

const LINKS = [
  ["/", "Home"],
  ["/browse", "Browse Items"],
  ["/feed", "Community Feed"],
  ["/my-reports", "My Reports"],
  ["/watchlist", "Watchlist"],
];

export const LogoMark = ({ className = "h-9 w-9" }) => (
  <svg viewBox="0 0 64 64" className={`${className} drop-shadow-sm`} aria-hidden="true">
    <defs><linearGradient id="b2u-g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#6366f1" /><stop offset="1" stopColor="#4338ca" /></linearGradient></defs>
    <rect width="64" height="64" rx="16" fill="url(#b2u-g)" />
    <path d="M32 12c-8.3 0-15 6.5-15 14.6C17 37.5 32 52 32 52s15-14.5 15-25.4C47 18.5 40.3 12 32 12z" fill="#fff" />
    <path d="M26.5 27.5a6 6 0 1 0 2-4.5" fill="none" stroke="#4f46e5" strokeWidth="3.2" strokeLinecap="round" />
    <path d="M25.2 19.6l3.6 3.6-4.6 1.4z" fill="#4f46e5" />
    <circle cx="48" cy="16" r="5" fill="#34d399" stroke="#fff" strokeWidth="2" />
  </svg>
);

export const Logo = ({ dark }) => (
  <span className="flex items-center gap-2.5 group" data-testid="brand-logo">
    <LogoMark className="h-9 w-9 transition-transform duration-300 group-hover:-rotate-6 group-hover:scale-105" />
    <span className={`text-xl font-extrabold tracking-tight ${dark ? "text-white" : "text-slate-900"}`}>
      Back<span className="bg-gradient-to-r from-indigo-500 to-emerald-500 bg-clip-text text-transparent">2</span>U
    </span>
  </span>
);

function useUnread(user) {
  const [count, setCount] = useState(0);
  const loc = useLocation();
  useEffect(() => {
    if (!user) return undefined;
    const load = () => api.get("/notifications").then((r) => setCount(r.data.unread)).catch(() => {});
    load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [user, loc.pathname]);
  return count;
}

export default function Navbar() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const unread = useUnread(user);
  const nav = useNavigate();
  const linkCls = ({ isActive }) =>
    `px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isActive ? "text-indigo-700 bg-indigo-50" : "text-slate-600 hover:text-slate-900 hover:bg-slate-100"}`;

  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-white/80 border-b border-slate-200/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
        <Link to="/" data-testid="nav-logo"><Logo /></Link>
        <nav className="hidden lg:flex items-center gap-1">
          {LINKS.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className={linkCls} data-testid={`nav-link-${label.toLowerCase().replace(/\s/g, "-")}`}>{label}</NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-2">
          {user && (
            <Link to="/notifications" data-testid="nav-notifications" className="relative p-2 rounded-lg hover:bg-slate-100" aria-label="Notifications">
              <Bell className="h-5 w-5 text-slate-700" />
              {unread > 0 && (
                <span data-testid="nav-unread-count" className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold grid place-items-center">{unread}</span>
              )}
            </Link>
          )}
          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button data-testid="nav-profile-menu" className="flex items-center gap-2 rounded-full border border-slate-200 pl-1 pr-3 py-1 hover:bg-slate-50">
                  <span className="h-7 w-7 rounded-full bg-indigo-100 text-indigo-700 grid place-items-center text-xs font-bold">{user.name?.[0]}</span>
                  <span className="hidden sm:inline text-sm font-medium text-slate-700 max-w-[110px] truncate">{user.name}</span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52">
                <DropdownMenuItem onClick={() => nav("/profile")} data-testid="menu-profile"><User className="h-4 w-4 mr-2" />Profile</DropdownMenuItem>
                <DropdownMenuItem onClick={() => nav("/my-reports")} data-testid="menu-my-reports"><FileText className="h-4 w-4 mr-2" />My Reports</DropdownMenuItem>
                {user.role === "admin" && (
                  <DropdownMenuItem onClick={() => nav("/admin")} data-testid="menu-admin"><Shield className="h-4 w-4 mr-2" />Admin Dashboard</DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={async () => { await logout(); nav("/"); }} data-testid="menu-logout"><LogOut className="h-4 w-4 mr-2" />Log out</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            user === false && (
              <div className="hidden sm:flex gap-2">
                <Button variant="ghost" onClick={() => nav("/login")} data-testid="nav-login-btn">Log in</Button>
                <Button onClick={() => nav("/register")} className="rounded-full bg-indigo-600 hover:bg-indigo-700" data-testid="nav-register-btn">Sign up</Button>
              </div>
            )
          )}
          <button className="lg:hidden p-2 rounded-lg hover:bg-slate-100" onClick={() => setOpen(!open)} data-testid="nav-mobile-toggle" aria-label="Menu">
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>
      {open && (
        <nav className="lg:hidden border-t border-slate-200 bg-white px-4 py-3 flex flex-col gap-1" data-testid="nav-mobile-menu">
          {LINKS.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"} className={linkCls} onClick={() => setOpen(false)}>{label}</NavLink>
          ))}
          <NavLink to="/notifications" className={linkCls} onClick={() => setOpen(false)}>Notifications</NavLink>
          <NavLink to="/profile" className={linkCls} onClick={() => setOpen(false)}>Profile</NavLink>
          {!user && <NavLink to="/login" className={linkCls} onClick={() => setOpen(false)}>Log in / Sign up</NavLink>}
        </nav>
      )}
    </header>
  );
}
