"""
Digital Sentinel — Email Tool
Fetches the last N unread email headers from two accounts:
  - Gmail   : OAuth 2.0 via credentials.json / token.json
  - Yahoo   : IMAP over SSL with an App Password

Also provides create_gmail_draft() for creating ready-to-send Gmail drafts
after Edwin reviews an application package. Uses a separate token
(token_compose.json) so the existing read-only auth is never disrupted.
"""
import base64
import os
import imaplib
import email
from email.header import decode_header
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

# ── Gmail (OAuth) ────────────────────────────────────────────────────────────
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# credentials.json and token.json live at the project root (digital-sentinel/)
# This file is at digital_sentinel/tools/email_tool.py — go up 3 levels.
_PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
_CREDENTIALS_PATH = os.path.join(_PROJECT_ROOT, "credentials.json")
_TOKEN_PATH = os.path.join(_PROJECT_ROOT, "token.json")
_TOKEN_COMPOSE_PATH = os.path.join(_PROJECT_ROOT, "token_compose.json")

_GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
_GMAIL_COMPOSE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]


def _get_gmail_service():
    """Returns an authenticated Gmail API service object (read-only)."""
    creds = None

    if os.path.exists(_TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(_TOKEN_PATH, _GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(_CREDENTIALS_PATH):
                raise FileNotFoundError(
                    "credentials.json not found. Download it from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                _CREDENTIALS_PATH, _GMAIL_SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _get_gmail_compose_service():
    """Returns an authenticated Gmail API service object with compose scope.

    Uses token_compose.json so the read-only token is never invalidated.
    First call opens a browser for a one-time approval of the compose scope.
    """
    creds = None

    if os.path.exists(_TOKEN_COMPOSE_PATH):
        creds = Credentials.from_authorized_user_file(
            _TOKEN_COMPOSE_PATH, _GMAIL_COMPOSE_SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(_CREDENTIALS_PATH):
                raise FileNotFoundError(
                    "credentials.json not found. Download it from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                _CREDENTIALS_PATH, _GMAIL_COMPOSE_SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(_TOKEN_COMPOSE_PATH, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def fetch_gmail_emails(max_results: int = 50) -> str:
    """Fetches the last unread emails from Gmail and returns their headers.

    Args:
        max_results: Maximum number of unread emails to retrieve (default 50).

    Returns:
        A formatted string listing each email's date, sender, and subject.
    """
    try:
        service = _get_gmail_service()
        result = (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX", "UNREAD"], maxResults=max_results)
            .execute()
        )
        messages = result.get("messages", [])
        if not messages:
            return "[Gmail] Inbox is clean — no unread messages."

        lines = []
        for msg in messages:
            detail = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                )
                .execute()
            )
            h = {hdr["name"]: hdr["value"] for hdr in detail["payload"]["headers"]}
            lines.append(
                f"  - [{h.get('Date', '?')}] From: {h.get('From', '?')} | Subject: {h.get('Subject', '(No Subject)')}"
            )

        return f"[Gmail] {len(lines)} unread emails:\n" + "\n".join(lines)

    except FileNotFoundError as e:
        return f"[Gmail] Setup Error: {e}"
    except Exception as e:
        return f"[Gmail] Error: {e}"


# ── Generic IMAP helper ───────────────────────────────────────────────────────

def _fetch_imap_emails(
    server: str, user: str, password: str, label: str, max_results: int = 50
) -> str:
    """Connects to an IMAP server over SSL and fetches unread email headers."""
    try:
        mail = imaplib.IMAP4_SSL(server, 993)
        mail.login(user, password)
        mail.select("inbox")

        _, data = mail.search(None, "UNSEEN")
        ids = data[0].split()
        if not ids:
            return f"[{label}] Inbox is clean — no unread messages."

        recent = ids[-max_results:]
        lines = []
        for eid in reversed(recent):
            _, raw = mail.fetch(eid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            msg = email.message_from_bytes(raw[0][1])

            subject_parts = decode_header(msg.get("Subject", "(No Subject)"))
            subject = "".join(
                part.decode(enc or "utf-8", errors="replace")
                if isinstance(part, bytes)
                else part
                for part, enc in subject_parts
            )

            lines.append(
                f"  - [{msg.get('Date', '?')}] From: {msg.get('From', '?')} | Subject: {subject}"
            )

        mail.logout()
        return f"[{label}] {len(lines)} unread emails:\n" + "\n".join(lines)

    except imaplib.IMAP4.error as e:
        return f"[{label}] IMAP Auth Error: {e}. Check your app password."
    except Exception as e:
        return f"[{label}] Error: {e}"


# ── Yahoo ─────────────────────────────────────────────────────────────────────

def fetch_yahoo_emails(max_results: int = 50) -> str:
    """Fetches the last unread emails from Yahoo Mail via IMAP.

    Args:
        max_results: Maximum number of unread emails to retrieve (default 50).

    Returns:
        A formatted string listing each email's date, sender, and subject.
    """
    user = os.getenv("YAHOO_USER")
    password = os.getenv("YAHOO_APP_PASSWORD")
    if not user or not password:
        return "[Yahoo] Error: YAHOO_USER or YAHOO_APP_PASSWORD missing from .env"
    return _fetch_imap_emails("imap.mail.yahoo.com", user, password, "Yahoo", max_results)


# ── Gmail Draft Creation ──────────────────────────────────────────────────────

def create_gmail_draft(to_email: str, subject: str, body: str) -> str:
    """Creates a Gmail draft ready for Edwin to review and send.

    The draft lands in Edwin's Gmail Drafts folder — nothing is sent until
    he opens Gmail and clicks Send. First call opens a browser for a
    one-time approval of the Gmail compose scope (token_compose.json).

    Args:
        to_email: Recipient email address (hiring manager, HR, etc.).
        subject: Email subject line.
        body: Full email body text (cover letter or cold outreach).

    Returns:
        Confirmation message with the Gmail draft ID, or an error description.
    """
    try:
        service = _get_gmail_compose_service()
        mime_msg = MIMEText(body, "plain", "utf-8")
        mime_msg["to"] = to_email
        mime_msg["subject"] = subject
        raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()
        draft = (
            service.users()
            .drafts()
            .create(userId="me", body={"message": {"raw": raw}})
            .execute()
        )
        return (
            f"Gmail draft created (ID: {draft['id']}).\n"
            f"To: {to_email}\n"
            f"Subject: {subject}\n"
            f"Open Gmail > Drafts to review and send. Nothing has been sent yet."
        )
    except FileNotFoundError as e:
        return f"[Gmail Draft] Setup Error: {e}"
    except Exception as e:
        return f"[Gmail Draft] Error creating draft: {e}"

