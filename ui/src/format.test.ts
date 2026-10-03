import { classTone, decisionTone, fmtDuration, fmtMs, fmtPct, fmtUsd, shortHash, statusTone } from "./format";

describe("formatters", () => {
  it("formats latency with sensible precision and tolerates missing values", () => {
    expect(fmtMs(0.3)).toBe("0.30 ms");
    expect(fmtMs(21.04)).toBe("21.0 ms");
    expect(fmtMs(780.4)).toBe("780 ms");
    expect(fmtMs(undefined)).toBe("–");
    expect(fmtMs(Number.NaN)).toBe("–");
  });
  it("formats money, percentages and hashes", () => {
    expect(fmtUsd(0.0025)).toBe("$0.0025");
    expect(fmtUsd(12.5)).toBe("$12.50");
    expect(fmtPct(72.04)).toBe("72%");
    expect(fmtPct(null)).toBe("no limit");
    expect(shortHash("a1f3c9d2e4b5f60718293a4b5c6d7e8f")).toBe("a1f3c9d2…7e8f");
  });
  it("maps decisions, classes and statuses to shape tones", () => {
    expect(decisionTone("BLOCK")).toBe("red"); // lime fill with a cross
    expect(decisionTone("APPROVAL")).toBe("yellow"); // lime outline
    expect(decisionTone("REDACT")).toBe("orange"); // dashed outline
    expect(decisionTone("ALLOW")).toBe("blue"); // grey outline
    expect(decisionTone(undefined)).toBe("gray");
    expect(classTone("public")).toBe("gray");
    expect(classTone("personal_data")).toBe("green");
    expect(classTone("bank_secret")).toBe("green");
    expect(statusTone("high_risk")).toBe("green");
    expect(statusTone("untrusted")).toBe("orange");
    expect(statusTone("clean")).toBe("blue");
  });
  it("reads durations the way a person would say them", () => {
    expect(fmtDuration(42)).toBe("42 s");
    expect(fmtDuration(120)).toBe("2 min");
    expect(fmtDuration(138)).toBe("2 min 18 s");
    expect(fmtDuration(3900)).toBe("1 h 5 min");
    expect(fmtDuration(null)).toBe("–");
    expect(fmtDuration(Number.NaN)).toBe("–");
  });
});
