from __future__ import annotations
from typing import Optional, List, Dict
import datetime as dt
import re

import dateparser
from pydantic import BaseModel

from config import settings
from tools.amadeus import AmadeusFlightTool

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    import anthropic
except Exception:
    anthropic = None


class ParsedIntent(BaseModel):
    intent: str
    origin: Optional[str] = None       
    destination: Optional[str] = None  
    date_from: Optional[dt.date] = None
    date_to: Optional[dt.date] = None
    adults: int = 1
    currency: str = "EUR"


def parse_user_message(msg: str) -> ParsedIntent:
    text = (msg or "").strip()
    lower = text.lower()

    origin = None
    destination = None
    adults = 1
    currency = "EUR"

    cities = re.findall(r"(istanbul|sabiha|ankara|izmir|paris|londra|london|berlin|new york)", lower)
    if cities:
        if len(cities) >= 2:
            origin, destination = cities[0], cities[1]
        else:
            destination = cities[0]

    date_from = None
    date_to = None
    rng = re.search(r"(\d{1,2} [a-zçğıöşü]+).*?(\d{1,2} [a-zçğıöşü]+)", lower)
    if rng:
        p1 = dateparser.parse(rng.group(1), languages=["tr", "en"])
        p2 = dateparser.parse(rng.group(2), languages=["tr", "en"])
        date_from = p1.date() if p1 else None
        date_to = p2.date() if p2 else None
    else:
        d = dateparser.parse(lower, languages=["tr", "en"])
        if d:
            date_from = d.date()

    keywords = ["uç", "uçak", "flight", "bilet", "fly"]
    if any(k in lower for k in keywords) and (destination or origin):
        return ParsedIntent(
            intent="flight_search",
            origin=origin,
            destination=destination,
            date_from=date_from,
            date_to=date_to,
            adults=adults,
            currency=currency,
        )

    return ParsedIntent(intent="chitchat")

_IATA_TO_CITY = {
    "LON": "London",
    "IST": "Istanbul",
    "SAW": "Istanbul (Sabiha Gökçen)",
    "ESB": "Ankara",
    "ADB": "Izmir",
    "PAR": "Paris",
    "BER": "Berlin",
    "NYC": "New York",
}

_IATA_LUT = {
    "istanbul": "IST",
    "ıstanbul": "IST",
    "sabiha": "SAW",
    "ankara": "ESB",
    "izmir": "ADB",
    "paris": "PAR",
    "londra": "LON",
    "london": "LON",
    "berlin": "BER",
    "new york": "NYC",
}

def to_iata(code_or_name: Optional[str], default: str) -> str:
    """
    Kullanıcı IATA girdiyse (3 harf) direkt kabul et; değilse LUT'tan çevir.
    Bulunamazsa default döner.
    """
    if not code_or_name:
        return default
    val = code_or_name.strip()
    if len(val) == 3 and val.isalpha():
        return val.upper()
    return _IATA_LUT.get(val.lower(), default)


class GPTAgent:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if (OpenAI and settings.OPENAI_API_KEY) else None
        self.model = settings.OPENAI_MODEL

    def chat(self, messages: List[dict]) -> str:
        if not self.client:
            last = messages[-1]["content"] if messages else ""
            return f"(Local GPT mock) You said: {last}"
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
        )
        return resp.choices[0].message.content


class ClaudeAgent:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY) if (anthropic and settings.ANTHROPIC_API_KEY) else None
        self.model = settings.ANTHROPIC_MODEL

    def translate(self, text: str, target_lang: str = "en") -> str:
        prompt = f"Translate the following text into {target_lang}. Keep prices and times intact.\n\n{text}"
        if not self.client:
            return f"(Local Claude mock) [{target_lang}] {text}"
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text


class Orchestrator:
    def __init__(self):
        self.gpt = GPTAgent()
        self.claude = ClaudeAgent()

        if not (settings.AMADEUS_API_KEY and settings.AMADEUS_API_SECRET):
            raise RuntimeError("Amadeus credentials are missing. Please set AMADEUS_API_KEY/SECRET in .env")

        self.flights = AmadeusFlightTool(
            client_id=settings.AMADEUS_API_KEY,
            client_secret=settings.AMADEUS_API_SECRET,
            env=getattr(settings, "AMADEUS_ENV", "test"),
        )
        self._iata_direct = True  
        
    def handle(self, user_text: str, want_translation: bool = False, target_lang: str = "en"):
        """
        Dönüş:
            base_reply (str),
            translated (Optional[str]),
            tool_results (List[Dict]),
            dest_label (Optional[str])  # Görsel üretimi için
        """
        intent = parse_user_message(user_text)

        tool_results: List[Dict] = []
        tool_note = None
        dest_label: Optional[str] = None

        if intent.intent == "flight_search":
            orig_code = to_iata(intent.origin, "IST")
            dest_code = to_iata(intent.destination, "LON")

            dest_label = intent.destination or _IATA_TO_CITY.get(dest_code, dest_code)

            if not dest_code:
                tool_note = "Could not resolve destination. Please specify a city/airport (IATA code)."
            else:
                date_from = intent.date_from or dt.date.today() + dt.timedelta(days=7)
                date_to = intent.date_to or date_from
                try:
                    tool_results = self.flights.search(
                        origin=orig_code,
                        destination=dest_code,
                        date_from=date_from,
                        date_to=date_to,
                        adults=intent.adults,
                        currency=intent.currency,
                    )
                except Exception as e:
                    tool_note = f"Flight search failed: {e}"

        sys_prompt = (
            "You are a travel planning assistant. If the user asked for flights, summarize options briefly. "
            "Include links if available."
        )
        messages = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_text},
        ]

        if tool_results:
            bullets = "\n".join(
                [
                    f"- {r.get('date')} {r.get('departure_time')} {r.get('origin')} → {r.get('destination')} — {r.get('airline')} — {r.get('price')}"
                    for r in tool_results[:5]
                ]
            )
            messages.append({"role": "system", "content": f"Flight summaries:\n{bullets}"})

        base_reply = self.gpt.chat(messages)

        if tool_results and "Flight summaries" not in base_reply:
            base_reply += "\n\n(See the options listed above.)"
        if tool_note:
            base_reply += f"\n\nNote: {tool_note}"

        translated = None
        if want_translation:
            translated = self.claude.translate(base_reply, target_lang=target_lang)

        return base_reply, translated, tool_results, dest_label
