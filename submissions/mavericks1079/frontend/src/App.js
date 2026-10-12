import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import Home from "@/pages/Home";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Browse from "@/pages/Browse";
import ItemDetail from "@/pages/ItemDetail";
import ReportItem from "@/pages/ReportItem";
import MyReports from "@/pages/MyReports";
import Watchlist from "@/pages/Watchlist";
import Notifications from "@/pages/Notifications";
import Profile from "@/pages/Profile";
import Feed from "@/pages/Feed";
import Handover from "@/pages/Handover";
import Scan from "@/pages/Scan";
import Receipt from "@/pages/Receipt";
import Admin from "@/pages/Admin";
import InfoPage from "@/pages/InfoPage";
import ReportMisuse from "@/pages/ReportMisuse";

const P = ({ children, admin }) => <ProtectedRoute admin={admin}>{children}</ProtectedRoute>;
const INFO = ["about", "how-it-works", "safety", "policy", "privacy", "terms", "help"];

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/browse" element={<Browse />} />
            <Route path="/feed" element={<Feed />} />
            <Route path="/items/:id" element={<ItemDetail />} />
            <Route path="/report/lost" element={<P><ReportItem mode="lost" /></P>} />
            <Route path="/report/found" element={<P><ReportItem mode="found" /></P>} />
            <Route path="/my-reports" element={<P><MyReports /></P>} />
            <Route path="/watchlist" element={<P><Watchlist /></P>} />
            <Route path="/notifications" element={<P><Notifications /></P>} />
            <Route path="/profile" element={<P><Profile /></P>} />
            <Route path="/handover/scan" element={<P><Scan /></P>} />
            <Route path="/handover/:id" element={<P><Handover /></P>} />
            <Route path="/receipts/:id" element={<P><Receipt /></P>} />
            <Route path="/admin" element={<P admin><Admin /></P>} />
            <Route path="/report-misuse" element={<P><ReportMisuse /></P>} />
            {INFO.map((slug) => (
              <Route key={slug} path={`/${slug}`} element={<InfoPage slug={slug} />} />
            ))}
            <Route path="*" element={<InfoPage slug="notfound" />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}

export default App;
