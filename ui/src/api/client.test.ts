import { api, ApiError, exportUrl } from "./client";

const ok = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
const mockFetch = (body: unknown) => vi.fn((_url: string, _init?: RequestInit) => ok(body));

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("requests the sessions endpoint with only the filters that are set", async () => {
    const fetchMock = mockFetch({ sessions: [] });
    vi.stubGlobal("fetch", fetchMock);
    await api.sessions({ agent: "kyc-agent", decision: "", data_class: "bank_secret" });
    expect(fetchMock.mock.calls[0][0]).toBe("/admin/sessions?agent=kyc-agent&data_class=bank_secret");
  });

  it("posts approval decisions as JSON", async () => {
    const fetchMock = mockFetch({ id: "a1", status: "denied" });
    vi.stubGlobal("fetch", fetchMock);
    await api.decide("a1", false, "officer");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/admin/approvals/a1/decide");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual({ approve: false, by: "officer" });
  });

  it("encodes session ids", async () => {
    const fetchMock = mockFetch({});
    vi.stubGlobal("fetch", fetchMock);
    await api.session("a/b c");
    expect(fetchMock.mock.calls[0][0]).toBe("/admin/sessions/a%2Fb%20c");
  });

  it("reads the signature feed hits", async () => {
    const fetchMock = mockFetch({ feed: {}, hits: [] });
    vi.stubGlobal("fetch", fetchMock);
    await api.signatures();
    expect(fetchMock.mock.calls[0][0]).toBe("/admin/signatures");
  });

  it("reads the time series for a window", async () => {
    const fetchMock = mockFetch({ bucket_s: 3600, points: [] });
    vi.stubGlobal("fetch", fetchMock);
    await api.timeseries();
    expect(fetchMock.mock.calls[0][0]).toBe("/admin/timeseries?window=24h");
  });

  it("turns error responses into ApiError with the server message", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({ detail: "unknown approval" }), { status: 404 }))));
    await expect(api.approvals()).rejects.toMatchObject({ status: 404, message: "unknown approval" });
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("boom", { status: 500, statusText: "Server Error" }))));
    await expect(api.metrics()).rejects.toBeInstanceOf(ApiError);
  });

  it("builds export URLs with only the set filters", () => {
    expect(exportUrl({ format: "csv", decision: "BLOCK", agent: "", owasp: "LLM01:2026" })).toBe(
      "/audit/export?format=csv&decision=BLOCK&owasp=LLM01%3A2026",
    );
    expect(exportUrl({ format: "jsonl" })).toBe("/audit/export?format=jsonl");
  });

  it("passes the event groups to the export", () => {
    expect(exportUrl({ format: "jsonl", events: "decisions,policy" })).toBe("/audit/export?format=jsonl&events=decisions%2Cpolicy");
  });
});
