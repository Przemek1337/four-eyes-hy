import { ChatPanel } from "../components/ChatPanel";

export function ChatView({ onOpenSession }: { onOpenSession?: (sessionId: string) => void }) {
  return (
    <section aria-label="Chat view">
      <h1 className="page-title">Chat</h1>
      <ChatPanel onOpenSession={onOpenSession} />
    </section>
  );
}
