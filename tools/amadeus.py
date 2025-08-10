from __future__ import annotations
import time, requests, datetime as dt
from typing import Any, Dict, List, Optional

class AmadeusFlightTool:
    def __init__(self, client_id: str, client_secret: str, env: str = "test"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base = "https://test.api.amadeus.com" if env != "prod" else "https://api.amadeus.com"
        self._token = None
        self._exp = 0

    def _auth(self) -> str:
        if self._token and time.time() < self._exp - 60:
            return self._token
        url = f"{self.base}/v1/security/oauth2/token"
        r = requests.post(url, data={
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }, timeout=20)
        r.raise_for_status()
        data = r.json()
        self._token = data["access_token"]
        self._exp = time.time() + int(data.get("expires_in", 1800))
        return self._token

    def search(self, origin: str, destination: str,
               date_from: dt.date, date_to: Optional[dt.date] = None,
               adults: int = 1, currency: str = "EUR", max_results: int = 10):
        """Uses Flight Offers Search (GET) for a simple one-way or date-range query."""
        token = self._auth()
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": date_from.isoformat(),
            "adults": adults,
            "currencyCode": currency,
            "max": max_results
        }

        if date_to and date_to != date_from:
            params["returnDate"] = date_to.isoformat()

        url = f"{self.base}/v2/shopping/flight-offers"
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        results = []
        for offer in data.get("data", []):
            itineraries = offer.get("itineraries", [])
            if not itineraries:
                continue
            first_leg = itineraries[0]["segments"][0]
            dep = first_leg["departure"]["at"]
            arr = first_leg["arrival"]["at"]
            airline = first_leg.get("carrierCode")
            price = offer.get("price", {}).get("grandTotal")
            results.append({
                "date": dep.split("T")[0],
                "departure_time": dep.split("T")[1][:5],
                "arrival_time": arr.split("T")[1][:5],
                "origin": first_leg["departure"]["iataCode"],
                "destination": first_leg["arrival"]["iataCode"],
                "airline": airline,
                "price": f"{price} {currency}",
                "link": "" 
            })
        return results
