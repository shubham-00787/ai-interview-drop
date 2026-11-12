"""Email the issue to the Brevo subscriber list as a campaign.
Brevo stores subscribers, handles confirmation emails and adds the unsubscribe link."""
import os
from datetime import datetime, timezone

import requests

from . import config

API = "https://api.brevo.com/v3"


def send_campaign(subject, html, attachment_url=None):
    key = os.getenv("BREVO_API_KEY")
    if not (key and config.BREVO_LIST_ID and config.SENDER_EMAIL):
        print("send: skipped (BREVO_API_KEY, BREVO_LIST_ID or SENDER_EMAIL not set); issue goes to the site only")
        return None
    h = {"api-key": key, "accept": "application/json", "content-type": "application/json"}
    r = requests.post(f"{API}/emailCampaigns", headers=h, timeout=60, json={
        "name": f"{subject} ({datetime.now(timezone.utc):%Y-%m-%d})",
        "subject": subject,
        "sender": {"name": config.SENDER_NAME, "email": config.SENDER_EMAIL},
        "type": "classic",
        "htmlContent": html,
        "recipients": {"listIds": [int(config.BREVO_LIST_ID)]},
        **({"attachmentUrl": attachment_url} if attachment_url else {}),
    })
    if r.status_code >= 400:
        print(f"send: Brevo said HTTP {r.status_code}: {r.text[:300]}")
    r.raise_for_status()
    cid = r.json()["id"]
    r = requests.post(f"{API}/emailCampaigns/{cid}/sendNow", headers=h, timeout=60)
    r.raise_for_status()
    print(f"send: Brevo campaign {cid} sent to list {config.BREVO_LIST_ID}")
    return cid
