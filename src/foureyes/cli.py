from __future__ import annotations

import argparse
import os
import threading
from pathlib import Path

import httpx
import uvicorn


def _real_upstreams(snapshot):
    from foureyes.upstream.openai_compat import OpenAICompatUpstream
    return {name: OpenAICompatUpstream(cfg["base_url"], cfg["type"]) for name, cfg in snapshot.policy.providers.items()}


def decision_registry_for(mock: bool, harness: str | None):
    from foureyes.semantic.decision_model_registry import DecisionModelRegistry
    from foureyes.semantic.mock_decision_client import MockDecisionClient

    if not mock:
        return DecisionModelRegistry()
    rules = {}
    if harness == "kyc":
        from harness.kyc.mock_decision_rules import MOCK_DECISION_RULES as rules
    return DecisionModelRegistry(override=MockDecisionClient(**rules))


def build(policy: Path, harness: str | None, port: int):
    from foureyes.api.app import create_app
    from foureyes.bootstrap import build_services
    from foureyes.semantic.injection import MockInjectionScorer
    from foureyes.semantic.judge import MockJudge, OllamaJudge
    from foureyes.upstream.base import UpstreamRegistry
    from foureyes.upstream.mcp import McpUpstream
    from foureyes.upstream.mock import MockModelUpstream

    mock = os.environ.get("MODEL", "").lower() == "mock"
    services = build_services(policy, audit_path=Path("data/audit.jsonl"), meter_path="data/budgets.db",
                              base_dir=policy.parent)
    snap = services.policy_store.current()
    tools_upstream, script, tools = None, None, None
    if harness == "kyc":
        from harness.kyc.mock_model import kyc_script
        from harness.kyc.server import create_tool_app
        from harness.kyc.tools import KycTools
        tools, script = KycTools(), kyc_script
        threading.Thread(target=lambda: uvicorn.run(create_tool_app(tools), host="127.0.0.1", port=port + 1,
                                                    log_level="warning"), daemon=True).start()
        tools_upstream = McpUpstream(f"http://127.0.0.1:{port + 1}/mcp")
    models = ({n: MockModelUpstream(c["type"], script=script) for n, c in snap.policy.providers.items()} if mock
              else _real_upstreams(snap))
    services.upstreams = UpstreamRegistry(models, tools_upstream)
    services.decision_models = decision_registry_for(mock, harness)
    if os.environ.get("FOUREYES_INJECTION", "mock") == "hf":
        from foureyes.semantic.injection import HFInjectionScorer
        services.injection = HFInjectionScorer()
    else:
        phrases = ()
        if harness == "kyc":
            from harness.kyc.data import HIDDEN_INSTRUCTION_PHRASES as phrases
        services.injection = MockInjectionScorer(extra_patterns=phrases)
    if not mock:
        local = snap.policy.providers["local"]
        model = snap.default_local_model(None)
        services.judge = OllamaJudge(local["base_url"], model)
    else:
        services.judge = MockJudge()
    app = create_app(services)
    if harness == "kyc":
        from harness.kyc.runner import make_document_runner
        client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=120.0)
        services.document_runner = make_document_runner(client, tools, os.environ.get("KYC_AGENT_KEY", ""))
    return app


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="foureyes")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--policy", default="policy.yaml")
    s.add_argument("--harness", choices=["kyc"], default=None)
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8080)
    args = p.parse_args(argv)
    Path("data").mkdir(exist_ok=True)
    for var in ("KYC_AGENT_KEY", "PLAYGROUND_AGENT_KEY", "ANETA_DEV_CLI_KEY"):
        os.environ.setdefault(var, f"dev-{var.lower()}")  # demo keys; set real ones in production
    uvicorn.run(build(Path(args.policy).resolve(), args.harness, args.port), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
