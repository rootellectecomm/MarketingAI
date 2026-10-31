"""Submit Rootellect's WhatsApp templates to Meta and report their approval status."""

from __future__ import annotations

import httpx

from app.core.config import Settings
from app.services.whatsapp_templates import TEMPLATES, meta_template_payload


async def sync_templates(settings: Settings, access_token: str, waba_id: str, *, submit: bool = True) -> list[dict]:
    """Create any missing templates (when ``submit``) and return the status of every Rootellect template.

    Existing templates are never modified; change copy by bumping the version
    suffix in ``whatsapp_templates.py``.
    """
    base = f"https://graph.facebook.com/{settings.meta_graph_version}/{waba_id}/message_templates"
    headers = {"Authorization": f"Bearer {access_token}"}
    wanted = {template.name: template for template in TEMPLATES.values()}
    results: list[dict] = []

    async with httpx.AsyncClient(timeout=30) as client:
        existing: dict[str, dict] = {}
        url: str | None = f"{base}?fields=name,status,category,rejected_reason&limit=200"
        while url:
            response = await client.get(url, headers=headers)
            data = response.json() if response.content else {}
            if not response.is_success:
                raise RuntimeError(f"Could not list templates: {response.status_code} {data}")
            for row in data.get("data", []):
                if row.get("name") in wanted:
                    existing[row["name"]] = row
            url = (data.get("paging") or {}).get("next")

        for name, template in wanted.items():
            if name in existing:
                row = existing[name]
                reason = row.get("rejected_reason")
                results.append(
                    {
                        "name": name,
                        "kind": template.kind,
                        "status": row.get("status"),
                        "category": row.get("category"),
                        "rejected_reason": reason if reason not in (None, "NONE") else None,
                    }
                )
                continue
            if not submit:
                results.append({"name": name, "kind": template.kind, "status": "NOT_SUBMITTED"})
                continue
            response = await client.post(
                base, headers=headers, json=meta_template_payload(template, settings.whatsapp_template_language)
            )
            data = response.json() if response.content else {}
            if response.is_success:
                status = data.get("status", "PENDING")
                results.append({"name": name, "kind": template.kind, "status": status, "category": data.get("category")})
            else:
                error = data.get("error") if isinstance(data, dict) else None
                message = (error or {}).get("error_user_msg") or (error or {}).get("message") or str(data)
                results.append({"name": name, "kind": template.kind, "status": "SUBMIT_FAILED", "error": message})
    return results
