import { useState } from "react";
import { Logo } from "./components/Logo";
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
  { id: "security", label: "Security", render: () => <SecurityView /> },
  { id: "management", label: "Management", render: () => <ManagementView /> },
  { id: "chat", label: "Chat", render: () => <ChatView /> },
] as const;

type TabId = (typeof TABS)[number]["id"];

function Shell() {
  const [tab, setTab] = useState<TabId>("security");
  const { connected } = useLive();
  const active = TABS.find((t) => t.id === tab)!;
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
          <span className={connected ? "live" : "ring"} aria-hidden="true" />
          {connected ? "Live" : "Checking every 5 s"}
        </div>
      </aside>
      <main className="main">{active.render()}</main>
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
