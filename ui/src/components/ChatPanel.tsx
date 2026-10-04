import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import type { ChatResult } from "../api/types";
import { fmtMs } from "../format";
import { DecisionPill } from "./Badge";

/** A file waiting to be sent. The gateway reads its text as an untrusted client document. */
interface Attachment { name: string; size: number; text: string }

const MAX_BYTES = 200 * 1024;
const TEXT_EXT = /\.(txt|md|csv|json|eml|log|xml|html?)$/i;

interface Item { id: number; text: string; attachment: Attachment | null; result: ChatResult }

const kb = (n: number): string => (n < 1024 ? `${n} B` : `${(n / 1024).toFixed(n < 10240 ? 1 : 0)} KB`);

/** Reads a text file in the browser. Rejects anything this demo cannot read as text, with a message that says what to do. */
export async function readAttachment(file: File): Promise<Attachment> {
  if (!TEXT_EXT.test(file.name) && !file.type.startsWith("text/")) {
    throw new Error(`${file.name} is not a text file. This demo reads .txt, .md, .csv, .json, .eml and .log files. Paste the text into a .txt file to test a PDF.`);
  }
  if (file.size > MAX_BYTES) throw new Error(`${file.name} is ${kb(file.size)}. The limit is ${kb(MAX_BYTES)}.`);
  const text = await new Promise<string>((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result ?? ""));
    r.onerror = () => reject(new Error(`Could not read ${file.name}.`));
    r.readAsText(file);
  });
  if (!text.trim()) throw new Error(`${file.name} is empty.`);
  return { name: file.name, size: file.size, text };
}

/** One plain sentence about what the gateway did. */
function headline(r: ChatResult, isDocument: boolean): string {
  if (isDocument && r.steps.length > 0) {
    const stopped = r.steps.filter((s) => s.outcome === "BLOCK").length;
    const held = r.steps.filter((s) => s.outcome === "APPROVAL").length;
    const parts = [`The agent took ${r.steps.length} step${r.steps.length === 1 ? "" : "s"}`];
    if (stopped) parts.push(`${stopped} stopped`);
    if (held) parts.push(`${held} held for a human`);
    return parts.join(", ");
  }
  if (r.decision === "BLOCK") return "Stopped before it reached the model";
  if (r.decision === "APPROVAL") return "Held for a human";
  if (r.decision === "REDACT") return "Allowed after removing sensitive parts";
  if (r.route?.type === "local") return "Answered by the local model";
  if (r.route) return "Answered by an external model";
  return "Allowed";
}

function Verdict({ item, onOpenSession }: { item: Item; onOpenSession?: (id: string) => void }) {
  const r = item.result;
  const stopped = r.decision === "BLOCK";
  const facts: [string, string][] = [];
  if (r.rule) facts.push(["Rule", r.rule]);
  if (r.layer) facts.push(["Checked by", r.layer === "ai" ? "AI" : "Rule, not AI"]);
  if (r.code) facts.push(["Code", r.code]);
  if (r.owasp.length > 0) facts.push(["OWASP", r.owasp.join(", ")]);
  if (r.injection_score != null) facts.push(["Injection score", r.injection_score.toFixed(2)]);
  if (r.data_class) facts.push(["Data class", r.data_class]);
  if (r.route) facts.push(["Route", `${r.route.type} · ${r.route.model} · router ${r.route.router}${r.route.rerouted_from ? ` (rerouted from ${r.route.rerouted_from})` : ""}`]);
  if (r.latency_ms != null) facts.push(["Time", fmtMs(r.latency_ms)]);
  const body = (
    <>
      <div className="verdict"><DecisionPill decision={r.decision} /><p>{headline(r, item.attachment != null)}</p></div>
      {facts.length > 0 && (
        <dl className="kv">
          {facts.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}
        </dl>
      )}
    </>
  );
  return (
    <article className="gw" aria-label={`Result ${item.id}`}>
      {stopped ? <div className="stopbox">{body}</div> : body}
      {r.steps.length > 0 && (
        <ol className="miniflow">
          {r.steps.map((s) => (
            <li key={s.n}>
              <DecisionPill decision={s.outcome} />
              <b className="mono">{`${s.n}. ${s.tool}`}</b>
              <span>{s.code ?? ""}</span>
            </li>
          ))}
        </ol>
      )}
      <p className="reply">{r.reply ?? r.message}</p>
      {r.approval_id && <p className="state state-warn">Waiting for approval {r.approval_id}. Open the session in Security to decide.</p>}
      {item.attachment && onOpenSession && (
        <button className="linkbtn open-session" onClick={() => onOpenSession(r.session_id)}>Open this session in Security</button>
      )}
    </article>
  );
}

function FileChip({ file, onRemove }: { file: Attachment; onRemove?: () => void }) {
  return (
    <span className="filechip">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8zM14 3v5h5" /></svg>
      <span className="fc-name">{file.name}</span>
      <small>{kb(file.size)}</small>
      {onRemove && <button className="fc-x" aria-label={`Remove ${file.name}`} onClick={onRemove}>✕</button>}
    </span>
  );
}

export function ChatPanel({ onOpenSession }: { onOpenSession?: (sessionId: string) => void }) {
  const [text, setText] = useState("");
  const [attachment, setAttachment] = useState<Attachment | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<Item[]>([]);
  const [dragging, setDragging] = useState(false);
  const inFlight = useRef(false);
  const end = useRef<HTMLDivElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    end.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [history.length]);

  const attach = async (file: File | undefined) => {
    if (!file) return;
    setError(null);
    try {
      setAttachment(await readAttachment(file));
      setText("");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const attachRef = useRef(attach);
  attachRef.current = attach;

  // A file dragged anywhere over the page lights up the box; dropping it anywhere attaches it,
  // so a miss never makes the browser navigate away to open the file.
  useEffect(() => {
    let depth = 0;
    const hasFiles = (e: DragEvent) => Array.from(e.dataTransfer?.types ?? []).includes("Files");
    const enter = (e: DragEvent) => { if (hasFiles(e)) { depth += 1; setDragging(true); } };
    const leave = (e: DragEvent) => { if (hasFiles(e)) { depth = Math.max(0, depth - 1); if (depth === 0) setDragging(false); } };
    const over = (e: DragEvent) => { if (hasFiles(e)) e.preventDefault(); };
    const drop = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      depth = 0;
      setDragging(false);
      void attachRef.current(e.dataTransfer?.files?.[0]);
    };
    window.addEventListener("dragenter", enter);
    window.addEventListener("dragleave", leave);
    window.addEventListener("dragover", over);
    window.addEventListener("drop", drop);
    return () => {
      window.removeEventListener("dragenter", enter);
      window.removeEventListener("dragleave", leave);
      window.removeEventListener("dragover", over);
      window.removeEventListener("drop", drop);
    };
  }, []);

  const grow = (el: HTMLTextAreaElement) => {
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  };

  const canSend = !busy && (attachment != null || text.trim() !== "");
  const send = async () => {
    if (inFlight.current || !canSend) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    try {
      const result = attachment
        ? await api.chat({ mode: "document", text: attachment.text, session_id: undefined }) // a file is a fresh client upload
        : await api.chat({ mode: "prompt", text, session_id: sessionId });
      if (!attachment) setSessionId(result.session_id);
      setHistory((h) => [...h, { id: (h[h.length - 1]?.id ?? 0) + 1, text: attachment ? "" : text, attachment, result }]);
      setText("");
      setAttachment(null);
      if (field.current) field.current.style.height = "auto";
    } catch (e) {
      setError((e as Error).message);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };

  return (
    <div className="chatwrap">
      <p className="page-sub">
        Type anything, or drop a file in. The same policy applies as for every agent. A file is sent as an untrusted client upload.
      </p>
      {sessionId && (
        <p className="chat-session">
          <span>{`Session ${sessionId}`}</span>
          <button className="linkbtn" onClick={() => setSessionId(undefined)}>New session</button>
        </p>
      )}

      <ol className="thread" aria-label="Conversation">
        {history.map((item) => (
          <li key={item.id}>
            <div className="me">
              {item.attachment && <FileChip file={item.attachment} />}
              {item.attachment
                ? <span className="me-doc">{item.attachment.text.length > 240 ? `${item.attachment.text.slice(0, 240)}…` : item.attachment.text}</span>
                : (item.text.length > 600 ? `${item.text.slice(0, 600)}…` : item.text)}
            </div>
            <Verdict item={item} onOpenSession={onOpenSession} />
          </li>
        ))}
      </ol>
      <div ref={end} />

      <div className={dragging ? "composer drop" : "composer"}>
        {dragging && <div className="drop-hint" role="status">Drop a file to attach it</div>}
        {attachment && <div className="attached"><FileChip file={attachment} onRemove={() => setAttachment(null)} /></div>}
        <div className="inrow">
          <button className="plus-btn" aria-label="Add an attachment" title="Add a file" onClick={() => fileInput.current?.click()}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
          </button>
          <label className="sr-only" htmlFor="chat-message">Message</label>
          <textarea id="chat-message" ref={field} aria-label="Message" rows={1} value={text} disabled={attachment != null}
                    placeholder={attachment ? "The file is sent as the client document. Remove it to type a message." : "Type a message, or drop a file here"}
                    onChange={(e) => { setText(e.target.value); grow(e.target); }}
                    onPaste={(e) => { const f = e.clipboardData?.files?.[0]; if (f) { e.preventDefault(); void attach(f); } }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(); }
                    }} />
          <button className="send" disabled={!canSend} onClick={() => void send()}>{busy ? "Sending…" : "Send"}</button>
          <input ref={fileInput} type="file" className="sr-only" tabIndex={-1} aria-label="Choose a file"
                 accept=".txt,.md,.csv,.json,.eml,.log,.xml,.html,text/*"
                 onChange={(e) => { void attach(e.target.files?.[0]); e.target.value = ""; }} />
        </div>
        {error && <p role="alert" className="state state-error">{error}</p>}
      </div>
    </div>
  );
}
