import pytest
from reporting import ReportPlugin


def pytest_configure(config):
    config.addinivalue_line("markers", "positive: benign case that must pass through")
    config.addinivalue_line("markers", "negative: attack case that must be stopped")
    config.addinivalue_line("markers", "owasp(id): OWASP LLM Top 10 (2026) category exercised by the test")
    config.pluginmanager.register(ReportPlugin(), "foureyes-report")


@pytest.fixture(autouse=True)
def no_live_registries(monkeypatch):
    """Tests never reach the live company registries, whatever the developer's shell exports."""
    monkeypatch.delenv("KRS_LIVE", raising=False)
    monkeypatch.delenv("CH_API_KEY", raising=False)
