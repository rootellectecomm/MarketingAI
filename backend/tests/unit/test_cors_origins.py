from app.core.config import Settings, get_cors_origin_regex, get_cors_origins


def test_cors_origins_include_connect_success_url():
    settings = Settings(
        backend_cors_origins="http://localhost:3000",
        meta_connect_success_url="https://marketing-ai-gamma-virid.vercel.app/settings",
    )
    origins = get_cors_origins(settings)
    assert "http://localhost:3000" in origins
    assert "https://marketing-ai-gamma-virid.vercel.app" in origins


def test_cors_regex_in_production():
    settings = Settings(environment="production")
    assert get_cors_origin_regex(settings) == r"https://.*\.vercel\.app$"
