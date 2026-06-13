from config import Settings


def test_cors_regex_allows_local_dev_by_default():
    settings = Settings(_env_file=None)

    assert "127\\.0\\.0\\.1" in settings.cors_allow_origin_regex
    assert "5174" in settings.cors_allow_origin_regex


def test_cors_regex_can_disable_local_dev():
    settings = Settings(_env_file=None, ALLOW_LOCAL_CORS=False)

    assert "127\\.0\\.0\\.1" not in settings.cors_allow_origin_regex
    assert "vercel" in settings.cors_allow_origin_regex


def test_render_defaults_to_production_without_local_cors(monkeypatch):
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-test")

    settings = Settings(_env_file=None)

    assert settings.app_env == "production"
    assert settings.allow_local_cors is False
    assert "127\\.0\\.0\\.1" not in settings.cors_allow_origin_regex


def test_public_frontend_url_extends_cors_and_admin_redirect():
    settings = Settings(
        _env_file=None,
        PUBLIC_FRONTEND_URL="https://frontend-staging.example.com/",
        ADMIN_FRONTEND_URL="https://frontend-production.example.com",
    )

    assert "https://frontend-staging.example.com" in settings.frontend_origin_list
    assert settings.admin_redirect_url == "https://frontend-staging.example.com/admin"


def test_public_backend_url_overrides_admin_callback_base():
    settings = Settings(
        _env_file=None,
        PUBLIC_BACKEND_URL="https://backend-staging.example.com/",
        ADMIN_PUBLIC_BASE_URL="https://backend-production.example.com",
    )

    assert settings.admin_callback_base_url == "https://backend-staging.example.com"
