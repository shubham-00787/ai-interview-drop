"""Send issues through your own Gmail account (lands in the inbox, free up to ~500 recipients/day).

Subscribers still live in Brevo (the Subscribe box adds them there); we read the list with the Brevo API.
Unsubscribing works by email: Gmail's built-in "Unsubscribe" button and the footer link both send a message
with the subject "unsubscribe" to your Gmail. Before every send we read those over IMAP and skip that person.
Only a SHA-256 hash of each unsubscribed address is stored (the repo is public).
"""
import email
import hashlib
import imaplib
import json
import os
import re
import smtplib
import time
from email.message import EmailMessage
from email.utils import formataddr, make_msgid, parseaddr

import requests

from . import config

UNSUBSCRIBED = config.DATA / "unsubscribed.json"
BREVO = "https://api.brevo.com/v3"


def configured():
    return bool(os.getenv("GMAIL_APP_PASSWORD") and config.SENDER_EMAIL)


def _h(addr):
    return hashlib.sha256(addr.strip().lower().encode()).hexdigest()


def _load_unsubscribed():
    return set(json.loads(UNSUBSCRIBED.read_text())) if UNSUBSCRIBED.exists() else set()


def unsubscribe_mailto():
    return f"mailto:{config.SENDER_EMAIL}?subject=unsubscribe"


def process_unsubscribes():
    """Read 'unsubscribe' emails from the Gmail inbox and remember the senders (hashed)."""
    done = _load_unsubscribed()
    try:
        im = imaplib.IMAP4_SSL("imap.gmail.com")
        im.login(config.SENDER_EMAIL, os.environ["GMAIL_APP_PASSWORD"].replace(" ", ""))
        im.select("INBOX")
        _, data = im.search(None, '(SUBJECT "unsubscribe")')
        ids = data[0].split()
        for i in ids:
            _, msg = im.fetch(i, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
            hdr = email.message_from_bytes(msg[0][1])
            if not re.search(r"\bunsubscribe\b", hdr.get("Subject", ""), re.I):
                continue
            addr = parseaddr(hdr.get("From", ""))[1]
            if addr and addr.lower() != config.SENDER_EMAIL.lower():
                done.add(_h(addr))
        im.logout()
    except (imaplib.IMAP4.error, OSError) as e:
        print(f"gmail: could not read unsubscribe requests ({e}); using the saved list")
    config.DATA.mkdir(exist_ok=True)
    UNSUBSCRIBED.write_text(json.dumps(sorted(done), indent=1) + "\n")
    return done


def subscribers():
    """Active contacts on the Brevo list (minus Brevo-blocklisted and email-unsubscribed people)."""
    h = {"api-key": os.environ["BREVO_API_KEY"], "accept": "application/json"}
    out, offset = [], 0
    while True:
        r = requests.get(f"{BREVO}/contacts/lists/{config.BREVO_LIST_ID}/contacts", headers=h, timeout=60,
                         params={"limit": 500, "offset": offset})
        r.raise_for_status()
        batch = r.json().get("contacts", [])
        out += [c["email"] for c in batch if c.get("email") and not c.get("emailBlacklisted")]
        if len(batch) < 500:
            break
        offset += 500
    gone = process_unsubscribes()
    active = sorted({e.lower() for e in out if _h(e) not in gone})
    print(f"gmail: {len(active)} active subscribers ({len(out) - len(active)} unsubscribed)")
    return active


def send_issue(subject, html, text, recipients=None):
    """Send one personal email per subscriber. Returns the number sent."""
    recipients = recipients if recipients is not None else subscribers()
    if len(recipients) > config.GMAIL_DAILY_LIMIT:
        print(f"gmail: {len(recipients)} subscribers is over the {config.GMAIL_DAILY_LIMIT}/day limit; "
              f"sending to the first {config.GMAIL_DAILY_LIMIT}")
        recipients = recipients[: config.GMAIL_DAILY_LIMIT]
    sent = 0
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(config.SENDER_EMAIL, os.environ["GMAIL_APP_PASSWORD"].replace(" ", ""))
        for to in recipients:
            m = EmailMessage()
            m["From"] = formataddr((config.SENDER_NAME, config.SENDER_EMAIL))
            m["To"] = to
            m["Subject"] = subject
            m["Message-ID"] = make_msgid(domain="gmail.com")
            m["List-Unsubscribe"] = f"<{unsubscribe_mailto()}>"
            m["List-Id"] = f"{config.NEWSLETTER_NAME} <interview-drop.{config.SENDER_EMAIL.split('@')[0]}>"
            m.set_content(text)
            m.add_alternative(html, subtype="html")
            try:
                s.send_message(m)
                sent += 1
            except smtplib.SMTPException as e:
                print(f"gmail: failed for one recipient: {e}")
            time.sleep(1.5)  # stay well under Gmail's rate limits
    print(f"gmail: sent to {sent} of {len(recipients)} subscribers")
    return sent
