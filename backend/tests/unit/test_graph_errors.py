from app.services.providers.graph_errors import format_graph_api_error


def test_format_graph_api_error_includes_body():
    data = {
        "error": {
            "message": "Invalid OAuth access token.",
            "type": "OAuthException",
            "code": 190,
            "error_subcode": 463,
        }
    }

    message = format_graph_api_error(data, status_code=401)

    assert "Invalid OAuth access token." in message
    assert "code=190" in message
    assert "status=401" in message
    assert "body=" in message
