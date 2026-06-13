from config import Settings


def test_cors_regex_allows_local_dev_by_default():
    settings = Settings(_env_file=None)

    assert "127\\.0\\.0\\.1" in settings.cors_allow_origin_regex
    assert "5174" in settings.cors_allow_origin_regex


def test_cors_regex_can_disable_local_dev():
    settings = Settings(_env_file=None, ALLOW_LOCAL_CORS=False)

    assert "127\\.0\\.0\\.1" not in settings.cors_allow_origin_regex
    assert "vercel" in settings.cors_allow_origin_regex
