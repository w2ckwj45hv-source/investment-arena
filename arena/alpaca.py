"""
Verbindung zum Broker Alpaca – NUR Paper-Trading (Spielgeld).

Die Orders sind echt: Sie gehen an den Broker und werden zu echten Marktpreisen
ausgeführt. Das Konto ist aber ein Übungskonto ohne echtes Geld.
Die Adresse unten ist fest auf das Paper-Konto eingestellt.
"""
import requests

from arena import settings

PAPER_URL = "https://paper-api.alpaca.markets"
SIGNUP_URL = "https://app.alpaca.markets/signup"


class AlpacaError(Exception):
    pass


class Alpaca:
    def __init__(self, key_id: str, secret: str):
        self.headers = {"APCA-API-KEY-ID": key_id, "APCA-API-SECRET-KEY": secret}

    def _req(self, method, path, **kw):
        try:
            r = requests.request(method, PAPER_URL + path, headers=self.headers, timeout=20, **kw)
        except requests.RequestException as e:
            raise AlpacaError(f"Keine Verbindung zu Alpaca ({e.__class__.__name__}).")
        if r.status_code in (401, 403):
            raise AlpacaError("Alpaca lehnt die Schlüssel ab. Bitte die Paper-Trading-Schlüssel prüfen.")
        if r.status_code >= 400:
            raise AlpacaError(f"Alpaca-Fehler {r.status_code}: {r.text[:200]}")
        return r.json() if r.text else None

    def account(self) -> dict:
        return self._req("GET", "/v2/account")

    def positions(self) -> list:
        return self._req("GET", "/v2/positions")

    def clock(self) -> dict:
        return self._req("GET", "/v2/clock")

    def order(self, order_id: str) -> dict:
        return self._req("GET", f"/v2/orders/{order_id}")

    def cancel_open_orders(self):
        return self._req("DELETE", "/v2/orders")

    def submit(self, symbol: str, qty: int, side: str) -> dict:
        """Marktorder. Außerhalb der Börsenzeit wird sie zur nächsten Eröffnung ausgeführt."""
        return self._req("POST", "/v2/orders", json={
            "symbol": symbol, "qty": str(int(qty)), "side": side,
            "type": "market", "time_in_force": "day"})


def configured() -> bool:
    return bool(settings.get("ALPACA_KEY_ID") and settings.get("ALPACA_SECRET_KEY"))


def client() -> Alpaca:
    if not configured():
        raise AlpacaError("Noch keine Alpaca-Schlüssel eingetragen.")
    return Alpaca(settings.get("ALPACA_KEY_ID"), settings.get("ALPACA_SECRET_KEY"))


def save_and_test(key_id: str, secret: str):
    """Testet die Schlüssel; speichert sie nur, wenn sie funktionieren. Gibt (ok, Nachricht) zurück."""
    try:
        acc = Alpaca(key_id.strip(), secret.strip()).account()
    except AlpacaError as e:
        return False, str(e)
    settings.set_many({"ALPACA_KEY_ID": key_id, "ALPACA_SECRET_KEY": secret})
    return True, f"Verbunden! Übungskonto mit {float(acc['equity']):,.0f} $ Spielgeld.".replace(",", ".")
