"""
Optionales Claude-Gehirn.

Ohne API-Schlüssel arbeitet das Team komplett mit seinen eigenen Regeln.
Mit Schlüssel schreibt Claude im Live-Betrieb zusätzlich eine verständliche
Zusammenfassung des Team-Meetings.

Schlüssel eintragen: Datei ".env" im Projektordner anlegen mit der Zeile
ANTHROPIC_API_KEY=sk-ant-...
"""
from arena import settings

MODEL = "claude-opus-5-5"


def _load_key():
    return settings.get("ANTHROPIC_API_KEY")


def available() -> bool:
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return bool(_load_key())


def summarize_meeting(transcript_text: str):
    """Lässt Claude das Meeting in 4–6 Sätzen auf Deutsch zusammenfassen. Gibt None bei Fehlern zurück."""
    if not available():
        return None
    import anthropic
    client = anthropic.Anthropic(api_key=_load_key())
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=("Du bist Protokollführer eines Investment-Teams aus sechs Agenten, das ein "
                    "virtuelles Übungsdepot verwaltet (keine echte Anlageberatung). Fasse das "
                    "Meeting in 4–6 klaren Sätzen auf Deutsch zusammen: Marktlage, wichtigste "
                    "Argumente, Entscheidungen und Risiken. Erfinde keine Zahlen."),
            messages=[{"role": "user", "content": transcript_text}],
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={"output_config": {"effort": "low"}, "fallbacks": "default"},
        )
    except Exception as e:
        return f"(Claude-Zusammenfassung nicht möglich: {e.__class__.__name__})"
    if resp.stop_reason == "refusal":
        return None
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip() or None
