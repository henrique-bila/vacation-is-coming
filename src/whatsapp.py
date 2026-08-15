"""Send WhatsApp messages (CallMeBot or Twilio)."""

from __future__ import annotations

import re
import time
from urllib.parse import quote

import requests

from .config import Settings

# CallMeBot uses GET; keep each part small after URL-encoding (unicode expands a lot).
MAX_CALLMEBOT_CHARS = 700
MAX_CALLMEBOT_URL_CHARS = 1800
MAX_CALLMEBOT_PARTS = 4
CHUNK_DELAY_SECONDS = 3.0


def normalize_callmebot_text(message: str) -> str:
    """Use ASCII-friendly punctuation for smaller, safer CallMeBot payloads."""
    return (
        message.replace("\u2014", "-")
        .replace("\u2192", "->")
        .replace("\u2013", "-")
    )


def split_message(message: str, max_chars: int = MAX_CALLMEBOT_CHARS) -> list[str]:
    """Pack route blocks into a few WhatsApp parts (CallMeBot rate limit: 16 / 4h)."""
    text = normalize_callmebot_text(message.strip())
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    parts = [part.strip() for part in text.split("\n\n") if part.strip()]
    if len(parts) <= 1:
        return _split_by_length(text, max_chars)

    title = parts[0]
    route_blocks = parts[1:]
    chunks: list[str] = []
    current_blocks: list[str] = []
    current_len = len(title)

    def flush(with_continuation: bool) -> None:
        nonlocal current_blocks, current_len
        if not current_blocks:
            return
        header = title if not chunks else f"{title} (cont.)"
        chunks.append("\n\n".join([header, *current_blocks]))
        current_blocks = []
        current_len = len(title)

    for block in route_blocks:
        extra = 2 if current_blocks else 2  # header separator
        if current_blocks and current_len + extra + len(block) > max_chars:
            flush(with_continuation=True)
        current_blocks.append(block)
        current_len += extra + len(block)

    flush(with_continuation=bool(chunks))

    if not chunks:
        return _split_by_length(text, max_chars)

    while len(chunks) > MAX_CALLMEBOT_PARTS:
        merged = f"{chunks[0]}\n\n{chunks[1]}"
        if len(merged) <= max_chars:
            chunks = [merged, *chunks[2:]]
        else:
            break

    return chunks


def _split_by_length(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    blocks = text.split("\n\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for block in blocks:
        extra = 2 if current else 0
        if current and current_len + extra + len(block) > max_chars:
            chunks.append("\n\n".join(current))
            current = [block]
            current_len = len(block)
        elif len(block) > max_chars:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                current_len = 0
            for start in range(0, len(block), max_chars):
                chunks.append(block[start : start + max_chars])
        else:
            current.append(block)
            current_len += extra + len(block)

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _format_callmebot_phone(raw_phone: str) -> tuple[str, str]:
    """Return (url_phone, masked) for CallMeBot. URL uses digits only, no '+'."""
    digits = re.sub(r"\D", "", raw_phone)
    if not digits:
        raise ValueError("CALLMEBOT_PHONE must contain digits with country code")
    if len(digits) < 10:
        raise ValueError("CALLMEBOT_PHONE looks too short; include country code (e.g. 5543...)")
    masked = f"{digits[:4]}***{digits[-4:]}" if len(digits) >= 8 else "***"
    return digits, masked


def _validate_callmebot_response(response_body: str) -> None:
    lowered = response_body.lower()
    if not lowered:
        raise RuntimeError("CallMeBot returned an empty response")

    if "message queued" in lowered or "added into the queue" in lowered:
        return

    failure_markers = (
        "apikey not valid",
        "apikey is invalid",
        "invalid apikey",
        "phone not registered",
        "not activated",
        "missing apikey",
        "missing phone",
    )
    if any(marker in lowered for marker in failure_markers):
        raise RuntimeError(f"CallMeBot returned an error: {response_body[:300]}")

    raise RuntimeError(
        "CallMeBot did not confirm delivery (expected 'Message queued'). "
        f"Response: {response_body[:300]}"
    )


def send_whatsapp(settings: Settings, message: str) -> int:
    """Send message via configured provider. Returns number of parts sent."""
    provider = settings.whatsapp_provider
    if provider == "callmebot":
        return _send_callmebot(settings, message)
    if provider == "twilio":
        return _send_twilio(settings, message)
    raise ValueError(
        f"Invalid WHATSAPP_PROVIDER: {provider!r}. Use 'callmebot' or 'twilio'."
    )


def _send_callmebot(settings: Settings, message: str) -> int:
    if not settings.callmebot_phone or not settings.callmebot_apikey:
        raise ValueError("Set CALLMEBOT_PHONE and CALLMEBOT_APIKEY")

    phone, masked_phone = _format_callmebot_phone(settings.callmebot_phone)
    apikey = settings.callmebot_apikey.strip()
    print(f"CallMeBot target phone: {masked_phone} ({len(phone)} digits)")
    print(f"CallMeBot apikey length: {len(apikey)}")
    chunks = split_message(message)
    total = len(chunks)

    for index, chunk in enumerate(chunks, start=1):
        body = chunk
        if total > 1:
            body = f"[{index}/{total}]\n{chunk}"

        url = (
            "https://api.callmebot.com/whatsapp.php"
            f"?phone={phone}"
            f"&text={quote(body)}"
            f"&apikey={quote(apikey)}"
        )
        if len(url) > MAX_CALLMEBOT_URL_CHARS:
            raise RuntimeError(
                f"CallMeBot URL too long ({len(url)} chars) for part {index}/{total}. "
                "Reduce routes or message size."
            )

        response = requests.get(url, timeout=30)
        response.raise_for_status()
        response_body = response.text.strip()
        print(f"CallMeBot part {index}/{total}: HTTP {response.status_code}, URL len {len(url)}")
        if response_body:
            print(f"CallMeBot response: {response_body[:300]}")

        _validate_callmebot_response(response_body)

        if index < total:
            time.sleep(CHUNK_DELAY_SECONDS)
    return total


def _send_twilio(settings: Settings, message: str) -> int:
    if not (
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_whatsapp_to
    ):
        raise ValueError(
            "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_TO"
        )

    to_number = settings.twilio_whatsapp_to
    if not to_number.startswith("whatsapp:"):
        to_number = f"whatsapp:{to_number}"

    from_number = settings.twilio_whatsapp_from
    if not from_number.startswith("whatsapp:"):
        from_number = f"whatsapp:{from_number}"

    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.twilio_account_sid}/Messages.json"
    )
    chunks = split_message(message)
    total = len(chunks)
    for index, chunk in enumerate(chunks, start=1):
        body = chunk
        if total > 1:
            body = f"[{index}/{total}]\n{chunk}"
        response = requests.post(
            url,
            data={"From": from_number, "To": to_number, "Body": body},
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            timeout=30,
        )
        response.raise_for_status()
        if index < total:
            time.sleep(CHUNK_DELAY_SECONDS)
    return total
