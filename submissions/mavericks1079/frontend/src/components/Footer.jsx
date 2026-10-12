import { Link } from "react-router-dom";
import { Logo } from "@/components/Navbar";

const LINKS = [
  ["/help", "Help"],
  ["/policy", "Responsible Use Policy"],
  ["/safety", "Safety Guidelines"],
  ["/privacy", "Privacy Policy"],
  ["/about", "About Back2U"],
  ["/how-it-works", "How it works"],
  ["/terms", "Terms"],
  ["/report-misuse", "Report Misuse"],
];

export default function Footer() {
  return (
    <footer className="bg-slate-950 text-slate-400 mt-16" data-testid="site-footer">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 flex flex-col md:flex-row gap-8 md:items-start md:justify-between">
        <div className="max-w-sm">
          <Logo dark />
          <p className="mt-3 text-sm leading-relaxed">Lost something? Let's bring it back to you. Recover honestly, respect ownership.</p>
        </div>
        <nav className="grid grid-cols-2 sm:grid-cols-4 gap-x-8 gap-y-3 text-sm">
          {LINKS.map(([to, label]) => (
            <Link key={to} to={to} className="hover:text-white transition-colors" data-testid={`footer-link-${to.slice(1)}`}>{label}</Link>
          ))}
        </nav>
      </div>
      <div className="border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 text-xs text-slate-500">© 2026 Back2U. A student-driven campus initiative.</div>
      </div>
    </footer>
  );
}
