import { aiSummary, pickAi } from "./aiInfo";
import type { AiInfo } from "./api/types";

const ai = (over: Partial<AiInfo> = {}): AiInfo => ({
  model: "granite_guardian", model_version: "g", rule: "fake_authority", probability: 0.97, confidence: 0.97,
  score: 0.97, chunks: 1, latency_ms: 40, uncertain: false, ...over,
});

describe("pickAi", () => {
  it("returns the assessment of the deciding control only, else null", () => {
    const both = { "data.classify_net": ai({ model: "basal" }), "sem.prompt_injection": ai() };
    expect(pickAi(both, "sem.prompt_injection")?.model).toBe("granite_guardian");
    expect(pickAi(both, "pipeline")).toBeNull();
    expect(pickAi(both)).toBeNull();
    expect(pickAi(null)).toBeNull();
    expect(pickAi({})).toBeNull();
  });
});

describe("aiSummary", () => {
  it("names model, rule, probability and confidence, and says when the model was not confident", () => {
    expect(aiSummary(ai())).toBe("granite_guardian · fake_authority · p 0.97 · confidence 0.97");
    expect(aiSummary(ai({ rule: null, uncertain: true, confidence: 0.6 }))).toBe("granite_guardian · p 0.97 · confidence 0.60 · not confident");
  });

  it("shows a dash instead of throwing when a number is missing", () => {
    const broken = ai({ probability: null as unknown as number, confidence: NaN });
    expect(aiSummary(broken)).toBe("granite_guardian · fake_authority · p – · confidence –");
  });
});
