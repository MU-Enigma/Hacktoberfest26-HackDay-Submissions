import { Outlet, Link } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useAuth } from "@/context/AuthContext";

function RestrictionBanner() {
  const { user } = useAuth();
  if (!user || user.status === "active") return null;
  return (
    <div data-testid="account-restriction-banner" className="bg-red-600 text-white text-sm">
      <div className="max-w-7xl mx-auto px-4 py-2 flex items-center gap-2">
        <ShieldAlert className="h-4 w-4" />
        Your account is {user.status}. Reporting, claiming and handovers are disabled.
        <Link to="/profile" className="underline font-semibold">Submit an appeal</Link>
      </div>
    </div>
  );
}

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <Navbar />
      <RestrictionBanner />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
