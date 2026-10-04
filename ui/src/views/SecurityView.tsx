import { useState } from "react";
import { api } from "../api/client";
import type { SessionFilters } from "../api/types";
import { ApprovalQueue } from "../components/ApprovalQueue";
import { ExportDialog } from "../components/ExportDialog";
import { SessionDetail } from "../components/SessionDetail";
import { SessionList } from "../components/SessionList";
import { usePolling } from "../hooks/usePolling";

export function SecurityView({ initialSessionId = null, onOpenChat }: { initialSessionId?: string | null; onOpenChat?: () => void }) {
  const [filters, setFilters] = useState<SessionFilters>({});
  const [selected, setSelected] = useState<string | null>(initialSessionId);
  const [exporting, setExporting] = useState(false);
  const sessions = usePolling(() => api.sessions(filters), [JSON.stringify(filters)]);
  const approvals = usePolling(() => api.approvals("pending"), []);

  if (selected) {
    return (
      <section aria-label="Security view">
        <button className="back" onClick={() => setSelected(null)}>← Sessions</button>
        <SessionDetail key={selected} sessionId={selected} onDecided={approvals.refresh} />
      </section>
    );
  }

  return (
    <section aria-label="Security view">
      <h1 className="page-title">Security</h1>
      <p className="page-sub">Every agent session and what FourEyes did with it.</p>
      <ApprovalQueue approvals={approvals.data?.approvals ?? []} onOpen={setSelected} />
      {sessions.error && sessions.data == null && (
        <div className="state-box" role="alert">
          <span>Could not load sessions: {sessions.error}</span>
          <button className="btn-sm retry" onClick={sessions.refresh}>Retry</button>
        </div>
      )}
      <SessionList
        rows={sessions.data?.sessions ?? []}
        onSelect={setSelected}
        filters={filters}
        onFilters={setFilters}
        onOpenChat={onOpenChat}
        actions={<button className="btn-sm" onClick={() => setExporting(true)}>Export audit log</button>}
      />
      <ExportDialog open={exporting} onClose={() => setExporting(false)} />
    </section>
  );
}
