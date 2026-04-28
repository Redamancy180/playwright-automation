from pw_automation.config import get_settings


def test_default_settings():
    settings = get_settings()
    assert settings.debug_port == 9555
    assert settings.default_timeout_ms == 600000
