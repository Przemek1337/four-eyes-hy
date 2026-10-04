import { fx } from "./test/fixtures";
import { buildSummaries } from "./managementSummary";

const all = () => ({
  metrics: fx.metrics(), series: fx.timeseries(), controls: fx.controls().map((c) => ({ ...c, status: "active" as const })),
  policy: fx.policy(), budgets: fx.budgets(), tests: fx.tests(), owasp: fx.owasp(),
});

describe("buildSummaries", () => {
  it("says in one sentence how each section is doing", () => {
    const s = buildSummaries(all());
    expect(s.threats?.text).toBe("118 blocked (9% of requests). Busiest hour: 12 at " + s.threats!.text.match(/at (\d\d:\d\d)\./)![1] + ". Most stopped by sig.feed.");
    expect(s.data?.text).toBe("No private data reached an external model. 61 fields were removed on the way.");
    expect(s.policy?.text).toBe("3 of 3 controls active, strict profile.");
    expect(s.speed?.text).toMatch(/The gateway adds 6\.0 ms at the median and 18\.0 ms at p95, 1\.5% of end-to-end time\./);
    expect(s.proof?.text).toBe("142 of 142 tests pass. Missed attacks 0, false blocks 0. 1 of 3 OWASP categories enforced.");
    expect(Object.values(s).every((x) => x && !x.attention || x?.attention === true)).toBe(true);
    expect(s.cost?.attention).toBe(true); // the fixture has agents near and over their limit
  });

  it("flags private data that reached an external model", () => {
    const s = buildSummaries({ ...all(), metrics: fx.metrics({ private_to_external: 3 }) });
    expect(s.data).toEqual({ text: "3 private request(s) reached an external model. This must be 0.", attention: true });
  });

  it("flags removed controls, a rejected policy and a feed error, in that order of importance", () => {
    expect(buildSummaries({ ...all(), controls: fx.controls() }).policy)
      .toEqual({ text: "dlp.redact_inflight removed. 2 of 3 controls active.", attention: true });
    const rejected = buildSummaries({ ...all(), policy: fx.policy({ error: "bad" }) }).policy;
    expect(rejected?.attention).toBe(true);
    expect(rejected?.text).toMatch(/rejected/);
    const feed = buildSummaries({ ...all(), policy: fx.policy({ feed: { ...fx.policy().feed, error: "boom" } }) }).policy;
    expect(feed?.text).toMatch(/signature feed has an error/);
  });

  it("names the budgets that are at or near their limit and says all is well otherwise", () => {
    const s = buildSummaries(all());
    expect(s.cost?.text).toMatch(/treasury-agent at its limit, playground-agent near its limit\./);
    const calm = buildSummaries({ ...all(), budgets: { agents: [], teams: [], blocked_by_budget: 0, fallbacks: 0 } });
    expect(calm.cost).toEqual({ text: "All budgets are within their limits. Spent $0.8400.", attention: false });
  });

  it("asks for a test report when there is none and flags missed attacks or false blocks", () => {
    expect(buildSummaries({ ...all(), tests: fx.tests({ ran_at: null }) }).proof)
      .toEqual({ text: "No test report yet.", attention: true });
    expect(buildSummaries({ ...all(), tests: fx.tests({ missed_attacks: 1 }) }).proof?.attention).toBe(true);
    expect(buildSummaries({ ...all(), tests: fx.tests({ false_blocks: 2 }) }).proof?.attention).toBe(true);
    expect(buildSummaries(all()).proof?.attention).toBe(false);
  });

  it("returns nothing for sections whose data has not arrived and copes with an idle gateway", () => {
    const none = buildSummaries({});
    expect(Object.values(none).every((x) => x === null)).toBe(true);
    const idle = fx.metrics({ requests: 0, by_decision: { ALLOW: 0, REDACT: 0, APPROVAL: 0, BLOCK: 0 },
      latency: { ...fx.metrics().latency, gateway: { count: 0, p50: 0, p95: 0 } }, top_blockers: [], redacted_fields: undefined });
    const s = buildSummaries({ metrics: idle });
    expect(s.threats?.text).toBe("0 blocked (0% of requests).");
    expect(s.speed?.text).toBe("No traffic yet.");
    expect(s.data?.text).toBe("No private data reached an external model.");
  });
});
