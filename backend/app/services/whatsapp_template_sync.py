"""Submit Rootellect's WhatsApp templates to Meta and report their approval status."""

from __future__ import annotations

import httpx

from app.core.config import Settings
from app.services.whatsapp_templates import TEMPLATES, meta_template_payload


async def _app_id(client: httpx.AsyncClient, settings: Settings, access_token: str) -> str:
    if settings.meta_app_id:
        return settings.meta_app_id
    response = await client.get(
        f"https://graph.facebook.com/{settings.meta_graph_version}/app", params={"access_token": access_token}
    )
    app_id = (response.json() if response.content else {}).get("id")
    if not response.is_success or not app_id:
        raise RuntimeError("Set META_APP_ID: needed to upload WhatsApp template header images")
    return str(app_id)


async def upload_header_example(client: httpx.AsyncClient, settings: Settings, access_token: str, image_url: str) -> str:
    """Upload an example header image with Meta's Resumable Upload API and return its handle."""
    image = await client.get(image_url, follow_redirects=True)
    if not image.is_success or not image.content:
        raise RuntimeError(f"Could not download header image {image_url}: HTTP {image.status_code}")
    content_type = (image.headers.get("content-type") or "image/jpeg").split(";")[0].strip()
    if content_type not in {"image/jpeg", "image/png"}:
        raise RuntimeError(f"Header image must be JPEG or PNG, got {content_type}: {image_url}")
    graph = f"https://graph.facebook.com/{settings.meta_graph_version}"
    session = await client.post(
        f"{graph}/{await _app_id(client, settings, access_token)}/uploads",
        params={
            "file_name": image_url.rsplit("/", 1)[-1],
            "file_length": str(len(image.content)),
            "file_type": content_type,
            "access_token": access_token,
        },
    )
    upload_id = (session.json() if session.content else {}).get("id")
    if not session.is_success or not upload_id:
        raise RuntimeError(f"Could not start header upload: {session.status_code} {session.text[:300]}")
    uploaded = await client.post(
        f"{graph}/{upload_id}",
        headers={"Authorization": f"OAuth {access_token}", "file_offset": "0"},
        content=image.content,
    )
    handle = (uploaded.json() if uploaded.content else {}).get("h")
    if not uploaded.is_success or not handle:
        raise RuntimeError(f"Header upload failed: {uploaded.status_code} {uploaded.text[:300]}")
    return str(handle)


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
            try:
                handle = (
                    await upload_header_example(client, settings, access_token, template.header_image)
                    if template.header_image
                    else None
                )
            except RuntimeError as exc:
                results.append({"name": name, "kind": template.kind, "status": "SUBMIT_FAILED", "error": str(exc)})
                continue
            response = await client.post(
                base,
                headers=headers,
                json=meta_template_payload(template, settings.whatsapp_template_language, header_handle=handle),
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
