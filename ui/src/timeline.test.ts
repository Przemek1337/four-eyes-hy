import { fx } from "./test/fixtures";
import { alertText, buildTimeline, headlineFor, summaryFor, taintedFrom } from "./timeline";

const events = [
  fx.decision({ decision_id: "d1", kind: "model", resource: "qwen2.5:7b", data_class: "public", labels: [],
    route: { allowed: ["local", "external"], chosen: "local", model: "qwen2.5:7b", router: "rule_based", rerouted_from: null, fallback: false } }),
  fx.decision({ decision_id: "d2", resource: "entities_documents_read", labels: ["untrusted", "high_risk"], data_class: "bank_secret",
    alerts: [{ kind: "document.injection", score: 0.95 }] }),
  { event: "class.raised", ts: "t", session_id: "a41f", from: "public", to: "bank_secret", reason: "source mcp:entities_documents_read" },
  fx.decision({ decision_id: "d3", resource: "entities_submit", decision: "BLOCK", rule: "authz.tools", code: "TOOL_ORDER",
    reason: "entities_submit requires sanctions_check first", labels: ["untrusted", "high_risk"] }),
];

describe("buildTimeline", () => {
  it("numbers decision steps, flags tainted ones and interleaves class notes", () => {
    const items = buildTimeline(events);
    expect(items.map((i) => [i.kind, i.n ?? null, i.tone, i.tainted])).toEqual([
      ["step", 1, "blue", false], ["step", 2, "orange", true], ["note", null, "orange", false], ["step", 3, "red", true],
    ]);
    expect(items[0].title).toBe("Model call");
    expect(items[0].route).toBe("local");
    expect(items[3].decision).toBe("BLOCK");
    expect(items[1].title).toBe("entities_documents_read");
    expect(items[2].summary).toBe("public → bank_secret (source mcp:entities_documents_read)");
  });
  it("ignores unrelated audit events", () => {
    expect(buildTimeline([{ event: "policy.reloaded", ts: "t", session_id: "x" }])).toEqual([]);
  });
  it("finds the step where the session first became untrusted", () => {
    expect(taintedFrom(buildTimeline(events))).toBe(2);
    expect(taintedFrom(buildTimeline([events[0]]))).toBeNull();
  });
});

describe("headlineFor", () => {
  const session = { ...fx.session(), scope: {}, task: null };
  it("says what the agent tried and that FourEyes stopped it", () => {
    expect(headlineFor(session, buildTimeline(events))).toBe("kyc-agent tried entities_submit and FourEyes stopped it");
  });
  it("says when an action waits for a human", () => {
    const held = buildTimeline([fx.decision({ decision_id: "h", resource: "send_email", decision: "APPROVAL" })]);
    expect(headlineFor(session, held)).toBe("kyc-agent tried send_email. It is waiting for a human");
  });
  it("describes a calm session and an empty one", () => {
    expect(headlineFor(session, buildTimeline([events[0]]))).toBe("kyc-agent ran 1 step and nothing was stopped");
    expect(headlineFor(session, [])).toBe("kyc-agent has not done anything yet");
    const model = buildTimeline([fx.decision({ decision_id: "m", kind: "model", decision: "BLOCK" })]);
    expect(headlineFor(session, model)).toBe("kyc-agent tried a model call and FourEyes stopped it");
  });
});

describe("summaryFor / alertText", () => {
  it("explains routing for model calls, and does not present the configured model as fact", () => {
    expect(summaryFor(events[0])).toBe("Route: public → local (qwen2.5:7b (as configured, the server did not say which model answered), router rule_based)");
  });
  it("names the model the server says answered, and says when the policy asked for another", () => {
    const route = { allowed: ["local"], chosen: "local", model: "qwen2.5:7b", router: "rule_based", rerouted_from: null, fallback: false };
    expect(summaryFor(fx.decision({ kind: "model", data_class: "public", route: { ...route, served_model: "qwen2.5:7b" } })))
      .toBe("Route: public → local (qwen2.5:7b, router rule_based)");
    expect(summaryFor(fx.decision({ kind: "model", data_class: "public", route: { ...route, served_model: "basal-1.0-1.5B" } })))
      .toBe("Route: public → local (basal-1.0-1.5B (the policy asked for qwen2.5:7b), router rule_based)");
  });
  it("explains stops with rule and code", () => {
    expect(summaryFor(events[3])).toContain("Blocked by authz.tools (TOOL_ORDER)");
  });
  it("mentions reroutes, external anonymization and alerts", () => {
    const text = summaryFor(fx.decision({ kind: "model", data_class: "public", anonymization: "not_applied",
      route: { allowed: ["local", "external"], chosen: "external", model: "ext-gpt-sim", router: "explicit", rerouted_from: "qwen2.5:7b", fallback: false } }));
    expect(text).toContain("rerouted from qwen2.5:7b");
    expect(text).toContain("anonymization not applied");
    expect(alertText({ kind: "document.injection", score: 0.95 })).toBe("Injection detector flagged the document (score 0.95)");
    expect(alertText({ kind: "budget.soft", pct: 85 })).toBe("Budget at 85%");
    expect(alertText({ kind: "judge.inconsistent" })).toBe("The AI judge found the action inconsistent with the task");
    expect(alertText({ kind: "output.canary" })).toBe("A canary from the system prompt appeared in the output");
    expect(alertText({ kind: "output.unsafe" })).toBe("Unsafe content found in the output");
    expect(alertText({ kind: "something.new" })).toBe("something.new");
  });
  it("defaults to Allowed and flags audit logging without redaction", () => {
    expect(summaryFor(fx.decision())).toBe("Allowed");
    expect(summaryFor(fx.decision({ redaction: "on" }))).toBe("Allowed");
    expect(summaryFor(fx.decision({ redaction: "off" }))).toBe("log redaction off");
  });
  it("tells fields removed before the model apart from plain redaction", () => {
    const ev = fx.decision({ decision: "REDACT", reason: "2 field(s) removed before the model sees them", detail: { dlp: "field_minimization", removed: 2 } });
    expect(summaryFor(ev)).toBe("2 field(s) removed before the model sees them");
  });
});
