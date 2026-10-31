"""Submit Rootellect's WhatsApp order templates to Meta for approval.

Usage (from backend/):
    python scripts/create_whatsapp_templates.py --dry-run     # print what would be submitted
    python scripts/create_whatsapp_templates.py               # submit templates that don't exist yet

Needs WHATSAPP_ACCESS_TOKEN (system user token with whatsapp_business_management)
and WHATSAPP_BUSINESS_ACCOUNT_ID (the WABA ID, not the phone number ID).
Existing templates with the same name are left untouched; to change copy,
bump the version suffix in app/services/whatsapp_templates.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.services.whatsapp_templates import TEMPLATES, meta_template_payload  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Print payloads without calling Meta")
    args = parser.parse_args()

    settings = get_settings()
    language = settings.whatsapp_template_language
    payloads = [meta_template_payload(template, language) for template in TEMPLATES.values()]

    if args.dry_run:
        print(json.dumps(payloads, indent=2, ensure_ascii=False))
        return 0

    token, waba_id = settings.whatsapp_access_token, settings.whatsapp_business_account_id
    if not token or not waba_id:
        print("Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_BUSINESS_ACCOUNT_ID first.", file=sys.stderr)
        return 2

    base = f"https://graph.facebook.com/{settings.meta_graph_version}/{waba_id}/message_templates"
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=30) as client:
        existing: dict[str, str] = {}
        url: str | None = f"{base}?fields=name,status,category&limit=200"
        while url:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            existing.update({row["name"]: f"{row.get('status')} ({row.get('category')})" for row in data.get("data", [])})
            url = (data.get("paging") or {}).get("next")

        failures = 0
        for payload in payloads:
            name = payload["name"]
            if name in existing:
                print(f"skip    {name}: already exists, {existing[name]}")
                continue
            response = client.post(base, headers=headers, json=payload)
            if response.is_success:
                body = response.json()
                print(f"created {name}: {body.get('status')} ({body.get('category')})")
            else:
                failures += 1
                print(f"FAILED  {name}: {response.status_code} {response.text}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
