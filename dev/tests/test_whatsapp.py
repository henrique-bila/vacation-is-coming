"""Tests for WhatsApp message splitting."""

from src.whatsapp import (
    _format_callmebot_phone,
    normalize_callmebot_text,
    split_message,
)


def test_split_message_keeps_short_messages():
    text = "Hello\n\nWorld"
    assert split_message(text) == [text]


def test_split_message_packs_multiple_routes():
    title = "Flight price alert"
    route_a = "*Londrina -> Recife*\n1. BRL 1,294.00"
    route_b = "*Londrina -> Salvador*\n1. BRL 1,204.00"
    route_c = "*Londrina -> Natal*\n1. BRL 2,076.00"
    message = f"{title}\n\n{route_a}\n\n{route_b}\n\n{route_c}"
    chunks = split_message(message, max_chars=200)
    assert len(chunks) < 3
    assert "Recife" in chunks[0]


def test_normalize_callmebot_text_replaces_unicode():
    text = "Londrina \u2192 Recife \u2014 LATAM"
    assert normalize_callmebot_text(text) == "Londrina -> Recife - LATAM"


def test_format_callmebot_phone_digits_only():
    phone, masked = _format_callmebot_phone("+55 43 99999-9999")
    assert phone == "5543999999999"
    assert "5543" in masked
    assert "9999" in masked
