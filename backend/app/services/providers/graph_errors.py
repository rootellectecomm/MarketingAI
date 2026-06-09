from __future__ import annotations

import json
from typing import Any


def format_graph_api_error(data: dict[str, Any] | Any, status_code: int | None = None) -> str:
    if not isinstance(data, dict):
        return json.dumps(data, default=str)

    error = data.get("error", data)
    if isinstance(error, dict):
        message = error.get("message") or "Unknown Graph API error"
        code = error.get("code")
        error_type = error.get("type")
        error_subcode = error.get("error_subcode")
        parts = [f"Graph API error: {message}"]
        if status_code is not None:
            parts.append(f"status={status_code}")
        if code is not None:
            parts.append(f"code={code}")
        if error_type:
            parts.append(f"type={error_type}")
        if error_subcode is not None:
            parts.append(f"subcode={error_subcode}")
        parts.append(f"body={json.dumps(data, default=str)}")
        return " ".join(parts)

    return json.dumps(data, default=str)
