import { AttackDemoBar } from "../components/AttackDemoBar";
import { ChatPanel } from "../components/ChatPanel";

export function ChatView({ onOpenSession }: { onOpenSession?: (sessionId: string) => void }) {
  return (
    <section aria-label="Playground view">
      <h1 className="page-title">Playground</h1>
      <AttackDemoBar />
      <ChatPanel onOpenSession={onOpenSession} />
    </section>
  );
}
