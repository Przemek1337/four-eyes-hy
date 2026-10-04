from reporting import ReportPlugin


def pytest_configure(config):
    config.addinivalue_line("markers", "positive: benign case that must pass through")
    config.addinivalue_line("markers", "negative: attack case that must be stopped")
    config.addinivalue_line("markers", "owasp(id): OWASP LLM Top 10 (2026) category exercised by the test")
    config.pluginmanager.register(ReportPlugin(), "foureyes-report")
