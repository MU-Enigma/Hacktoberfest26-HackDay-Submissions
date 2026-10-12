import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Search, PackageSearch, HandHeart, ShieldCheck, Sparkles, ArrowRight, Undo2, MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ItemCard, EmptyState } from "@/components/ItemCard";
import { useAuth } from "@/context/AuthContext";
import { api, timeAgo } from "@/lib/api";

const Stat = ({ label, value, testId }) => (
  <div className="card-surface p-5">
    <div className="text-3xl font-extrabold text-slate-900 tracking-tight" data-testid={testId}>{value ?? "-"}</div>
    <div className="text-sm text-slate-500 mt-1">{label}</div>
  </div>
);

function Hero() {
  const nav = useNavigate();
  const [q, setQ] = useState("");
  return (
    <section className="relative overflow-hidden grid-bg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14 lg:py-20 grid lg:grid-cols-[1.15fr_1fr] gap-10 items-center">
        <div className="fade-up">
          <span className="overline-label">Campus lost & found, made intelligent</span>
          <h1 className="mt-4 text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 leading-[1.05]">
            Lost something? <span className="text-indigo-600">Let's bring it back to you.</span>
          </h1>
          <p className="mt-5 text-base md:text-lg text-slate-600 max-w-xl">Report in under a minute. Our ML engine matches lost and found reports, private clues protect ownership, and QR handovers close the loop safely.</p>
          <div className="mt-8 flex flex-col sm:flex-row gap-3">
            <Button size="lg" onClick={() => nav("/report/lost")} data-testid="hero-lost-btn" className="h-14 px-8 rounded-full text-base font-bold bg-amber-500 hover:bg-amber-600 shadow-lg shadow-amber-500/20">
              <PackageSearch className="h-5 w-5 mr-2" /> I LOST IT
            </Button>
            <Button size="lg" onClick={() => nav("/report/found")} data-testid="hero-found-btn" className="h-14 px-8 rounded-full text-base font-bold bg-emerald-600 hover:bg-emerald-700 shadow-lg shadow-emerald-600/20">
              <HandHeart className="h-5 w-5 mr-2" /> I FOUND IT
            </Button>
          </div>
          <form onSubmit={(e) => { e.preventDefault(); nav(`/browse?q=${encodeURIComponent(q)}`); }} className="mt-8 flex gap-2 max-w-xl">
            <div className="relative flex-1">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search items, categories, locations..." className="h-12 pl-10 rounded-full bg-white" data-testid="hero-search-input" />
            </div>
            <Button type="submit" className="h-12 rounded-full px-6 bg-indigo-600 hover:bg-indigo-700" data-testid="hero-search-btn">Search</Button>
          </form>
        </div>
        <div className="relative hidden lg:block fade-up" style={{ animationDelay: "120ms" }}>
          <img src="/hero.jpg" alt="Students on campus" className="rounded-3xl h-[440px] w-full object-cover shadow-xl" />
          <div className="absolute -bottom-6 -left-6 card-surface p-4 flex items-center gap-3 shadow-lg">
            <ShieldCheck className="h-8 w-8 text-emerald-600" />
            <div>
              <div className="font-semibold text-slate-900 text-sm">Verified handovers only</div>
              <div className="text-xs text-slate-500">Two-party QR confirmation</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

const SectionHead = ({ over, title, to, testId }) => (
  <div className="flex items-end justify-between mb-6">
    <div>
      <span className="overline-label">{over}</span>
      <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 mt-1">{title}</h2>
    </div>
    {to && <Link to={to} className="text-sm font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1" data-testid={testId}>View all <ArrowRight className="h-4 w-4" /></Link>}
  </div>
);

function MatchesSection({ user, feedMatches }) {
  const [mine, setMine] = useState([]);
  useEffect(() => {
    if (user) api.get("/matches/mine").then((r) => setMine(r.data)).catch(() => {});
  }, [user]);
  const list = user && mine.length ? mine.map((m) => ({ id: m.id, score: m.score, a: m.mine, b: m.other, personal: true })) : feedMatches.map((m) => ({ id: m.id, score: m.score, a: m.lost, b: m.found }));
  return (
    <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12" data-testid="potential-matches-section">
      <SectionHead over="ML matching engine" title={user && mine.length ? "Potential matches for your reports" : "Potential matches on campus"} />
      {list.length === 0 ? (
        <EmptyState icon={Sparkles} title="No potential matches yet" text="When a lost and a found report look alike, they appear here with a match score." />
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {list.slice(0, 6).map((m) => (
            <Link key={m.id} to={`/items/${m.personal ? m.a.id : m.b.id}`} data-testid={`match-card-${m.id}`} className="card-surface p-5 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500">{m.personal ? "Your report" : "Lost"} ↔ {m.personal ? "Possible match" : "Found"}</span>
                <span className="font-mono font-bold text-indigo-700 bg-indigo-50 rounded-lg px-2 py-0.5 text-sm">{m.score}%</span>
              </div>
              <div className="mt-3 font-semibold text-slate-900 truncate">{m.a.title}</div>
              <div className="text-sm text-slate-500 truncate">{m.b.title}</div>
              <div className="mt-2 text-xs text-slate-400 flex items-center gap-1"><MapPin className="h-3 w-3" />{m.b.location}</div>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}

export default function Home() {
  const { user } = useAuth();
  const [recent, setRecent] = useState(null);
  const [feed, setFeed] = useState({ matches: [], stories: [], stats: {} });
  useEffect(() => {
    api.get("/items", { params: { limit: 8 } }).then((r) => setRecent(r.data.items)).catch(() => setRecent([]));
    api.get("/feed").then((r) => setFeed(r.data)).catch(() => {});
  }, []);
  const s = feed.stats || {};

  return (
    <div data-testid="home-page">
      <Hero />
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <SectionHead over="Fresh on the board" title="Recently reported items" to="/browse" testId="home-view-all-items" />
        {recent === null ? <div className="text-slate-400">Loading...</div> : recent.length === 0 ? (
          <EmptyState icon={PackageSearch} title="No reports yet" text="Be the first to report a lost or found item." />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">{recent.map((i) => <ItemCard key={i.id} item={i} />)}</div>
        )}
      </section>
      <MatchesSection user={user} feedMatches={feed.matches || []} />
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12" data-testid="stats-section">
        <SectionHead over="Live from our database" title="Community recovery stats" />
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <Stat label="Lost reports" value={s.lost} testId="stat-lost" />
          <Stat label="Found reports" value={s.found} testId="stat-found" />
          <Stat label="Items returned" value={s.returned} testId="stat-returned" />
          <Stat label="Active matches" value={s.active_matches} testId="stat-matches" />
          <Stat label="Avg. days to return" value={s.avg_days_to_return ?? "-"} testId="stat-avg-days" />
        </div>
      </section>
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 grid lg:grid-cols-[1.4fr_1fr] gap-6">
        <div>
          <SectionHead over="Anonymized" title="Recent successful recoveries" to="/feed" testId="home-view-feed" />
          {feed.stories?.length ? (
            <div className="space-y-3" data-testid="recoveries-list">
              {feed.stories.map((st) => (
                <div key={st.id} className="card-surface p-4 flex items-center gap-4">
                  <span className="h-10 w-10 rounded-xl bg-green-100 text-green-700 grid place-items-center"><Undo2 className="h-5 w-5" /></span>
                  <div className="text-sm text-slate-700">A <b>{st.category_label}</b> item found near <b>{st.location}</b> was returned to its owner <span className="text-slate-400">· {timeAgo(st.completed_at)}</span></div>
                </div>
              ))}
            </div>
          ) : <EmptyState icon={Undo2} title="No recoveries yet" text="Completed QR handovers will appear here without any personal details." />}
        </div>
        <div className="rounded-2xl bg-indigo-600 text-white p-8 flex flex-col justify-between" data-testid="honesty-reminder">
          <ShieldCheck className="h-10 w-10 text-indigo-200" />
          <div>
            <h3 className="text-2xl font-bold mt-6">Report honestly. Respect ownership.</h3>
            <p className="text-indigo-100 mt-2 text-sm leading-relaxed">False claims, fake reports or withholding found items can lead to suspension, bans and referral to university authorities.</p>
            <Link to="/policy" className="inline-flex items-center gap-1 mt-5 font-semibold text-white underline underline-offset-4" data-testid="home-policy-link">Read the Responsible Use Policy <ArrowRight className="h-4 w-4" /></Link>
          </div>
        </div>
      </section>
    </div>
  );
}
