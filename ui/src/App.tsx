import { useState } from "react";
import { Logo } from "./components/Logo";
import { ConnectionBanner } from "./components/ConnectionBanner";
import { LiveProvider, useLive } from "./live";
import { ChatView } from "./views/ChatView";
import { ManagementView } from "./views/ManagementView";
import { SecurityView } from "./views/SecurityView";

const ICONS = {
  security: "M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z",
  management: "M4 20V10M10 20V4M16 20v-7M22 20H2",
  chat: "M21 12a8 8 0 01-11.6 7.1L4 20l1-4.6A8 8 0 1121 12z",
};

const TABS = [
  { id: "security", label: "Security" },
  { id: "management", label: "Management" },
  { id: "chat", label: "Chat" },
] as const;

type TabId = (typeof TABS)[number]["id"];

function Shell() {
  const [tab, setTab] = useState<TabId>("security");
  const [openSession, setOpenSession] = useState<{ id: string; n: number } | null>(null);
  const { connected, offline } = useLive();
  return (
    <div className="app">
      <aside className="side">
        <Logo />
        <nav className="nav" role="tablist" aria-orientation="vertical" aria-label="Views">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              aria-selected={t.id === tab}
              className={t.id === tab ? "tab active" : "tab"}
              onClick={() => setTab(t.id)}
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d={ICONS[t.id]} />
              </svg>
              {t.label}
            </button>
          ))}
        </nav>
        <div className="side-foot" role="status">
          <span className={offline ? "off" : connected ? "live" : "ring"} aria-hidden="true" />
          {offline ? "Offline" : connected ? "Live" : "Checking every 5 s"}
        </div>
      </aside>
      <main className="main">
        <ConnectionBanner />
        {tab === "security" && <SecurityView key={openSession?.n ?? 0} initialSessionId={openSession?.id ?? null} onOpenChat={() => setTab("chat")} />}
        {tab === "management" && <ManagementView />}
        {tab === "chat" && <ChatView onOpenSession={(id) => { setOpenSession({ id, n: (openSession?.n ?? 0) + 1 }); setTab("security"); }} />}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <LiveProvider>
      <Shell />
    </LiveProvider>
  );
}
