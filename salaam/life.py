"""
Everyday-life data: weather, markets, currency and prayer times.

All sources are keyless public APIs (Open-Meteo, CoinGecko, exchangerate-api,
AlAdhan) so Salaam is useful the moment it starts, with no billing setup.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

from salaam import net
from salaam.config import config

# Open-Meteo WMO weather codes → plain English, because "code 63" means
# nothing when it is being read out loud.
WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "freezing drizzle",
    57: "heavy freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "freezing rain",
    67: "heavy freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light showers",
    81: "showers",
    82: "violent showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with heavy hail",
}

# Friendly name → CoinGecko id, so users can say "bitcoin" not "wrapped-bitcoin".
COINS = {
    "bitcoin": "bitcoin",
    "btc": "bitcoin",
    "ethereum": "ethereum",
    "eth": "ethereum",
    "solana": "solana",
    "sol": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "cardano": "cardano",
    "ada": "cardano",
    "dogecoin": "dogecoin",
    "doge": "dogecoin",
    "tron": "tron",
    "usdt": "tether",
    "tether": "tether",
}


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------


async def geocode(place: str) -> dict[str, Any] | None:
    """Resolve a place name to coordinates."""
    data = await net.get_json(
        f"https://geocoding-api.open-meteo.com/v1/search?name={quote_plus(place)}&count=1"
    )
    results = (data or {}).get("results") or []
    return results[0] if results else None


async def weather(place: str | None = None) -> dict[str, Any] | None:
    """Current conditions plus a short forecast for a place."""
    place = place or config.HOME_CITY
    location = await geocode(place)
    if not location:
        return None

    data = await net.get_json(
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={location['latitude']}&longitude={location['longitude']}"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
        "precipitation,weather_code,wind_speed_10m"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max"
        "&forecast_days=3&timezone=auto"
    )
    if not data or "current" not in data:
        return None

    return {"location": location, "current": data["current"], "daily": data.get("daily", {})}


def describe_weather(payload: dict[str, Any]) -> str:
    location = payload["location"]
    current = payload["current"]
    daily = payload.get("daily", {})

    name = ", ".join(
        part for part in (location.get("name"), location.get("country")) if part
    )
    condition = WEATHER_CODES.get(current.get("weather_code"), "unclear conditions")

    lines = [
        f"### Weather — {name}",
        f"Right now: {condition}, {current.get('temperature_2m')}°C "
        f"(feels like {current.get('apparent_temperature')}°C).",
        f"Humidity {current.get('relative_humidity_2m')}%, "
        f"wind {current.get('wind_speed_10m')} km/h.",
    ]

    days = daily.get("time") or []
    if days:
        lines.append("")
        lines.append("Next few days:")
        for index, day in enumerate(days[:3]):
            label = datetime.fromisoformat(day).strftime("%a %d %b")
            code = WEATHER_CODES.get(daily["weather_code"][index], "mixed")
            low = daily["temperature_2m_min"][index]
            high = daily["temperature_2m_max"][index]
            rain = daily.get("precipitation_probability_max", [None] * 3)[index]
            rain_text = f", {rain}% chance of rain" if rain is not None else ""
            lines.append(f"- {label}: {code}, {low}–{high}°C{rain_text}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markets
# ---------------------------------------------------------------------------


async def crypto_prices(symbols: list[str] | None = None) -> dict[str, Any] | None:
    wanted = symbols or ["bitcoin", "ethereum", "solana", "binancecoin", "ripple"]
    ids = ",".join(sorted({COINS.get(symbol.lower(), symbol.lower()) for symbol in wanted}))
    return await net.get_json(
        f"https://api.coingecko.com/api/v3/simple/price?ids={ids}"
        "&vs_currencies=usd&include_24hr_change=true&include_market_cap=true"
    )


async def fx_rates(base: str = "USD") -> dict[str, Any] | None:
    return await net.get_json(f"https://open.er-api.com/v6/latest/{base.upper()}")


def describe_markets(crypto: dict[str, Any] | None, fx: dict[str, Any] | None) -> str:
    lines = ["### Markets"]

    if crypto:
        lines.append("")
        lines.append("**Crypto (USD)**")
        for coin_id, values in crypto.items():
            price = values.get("usd")
            change = values.get("usd_24h_change")
            arrow = "▲" if (change or 0) >= 0 else "▼"
            change_text = f" {arrow} {change:+.2f}% (24h)" if change is not None else ""
            lines.append(f"- {coin_id.title()}: ${price:,.2f}{change_text}")

    if fx and fx.get("rates"):
        rates = fx["rates"]
        base = fx.get("base_code", "USD")
        lines.append("")
        lines.append(f"**Currency (1 {base})**")
        for code in ("NGN", "EUR", "GBP", "GHS", "ZAR", "KES"):
            if code in rates:
                lines.append(f"- {code}: {rates[code]:,.2f}")
        lines.append("")
        lines.append(
            "_Official/interbank rates. Nigerian parallel-market rates differ "
            "and are not published by any reliable free feed._"
        )

    if len(lines) == 1:
        return "I couldn't reach the market data providers just now."
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prayer times
# ---------------------------------------------------------------------------

PRAYERS = ("Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha")


async def prayer_times(city: str | None = None, country: str | None = None) -> dict[str, Any] | None:
    city = city or config.HOME_CITY
    country = country or config.HOME_COUNTRY
    data = await net.get_json(
        "https://api.aladhan.com/v1/timingsByCity"
        f"?city={quote_plus(city)}&country={quote_plus(country)}&method=2"
    )
    if not data or data.get("code") != 200:
        return None
    return data.get("data")


def describe_prayer_times(payload: dict[str, Any], city: str, country: str) -> str:
    timings = payload.get("timings", {})
    date_info = payload.get("date", {})
    hijri = date_info.get("hijri", {})
    hijri_text = ""
    if hijri:
        month = (hijri.get("month") or {}).get("en", "")
        hijri_text = f" ({hijri.get('day', '')} {month} {hijri.get('year', '')} AH)"

    lines = [
        f"### Prayer times — {city}, {country}{hijri_text}",
        f"_{date_info.get('readable', '')}_",
        "",
    ]
    for prayer in PRAYERS:
        if prayer in timings:
            lines.append(f"- {prayer}: {timings[prayer]}")
    return "\n".join(lines)
