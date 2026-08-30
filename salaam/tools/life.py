"""
Everyday-life tools — weather, markets, currency conversion, prayer times.
"""

from __future__ import annotations

from salaam import life, net
from salaam.config import config


def register(mcp):

    @mcp.tool()
    async def get_weather(city: str = "") -> str:
        """
        Current weather and a three-day forecast for any city worldwide.
        Defaults to the user's home city when none is given.
        """
        place = city.strip() or config.HOME_CITY
        payload = await life.weather(place)
        if not payload:
            return f"I couldn't find weather data for \"{place}\". Try a nearby larger city."
        return life.describe_weather(payload)

    @mcp.tool()
    async def get_markets(coins: str = "") -> str:
        """
        Crypto prices with 24-hour movement, plus major currency rates
        including the naira.

        Args:
            coins: optional comma-separated list, e.g. "bitcoin, solana".
                   Leave empty for the default basket.
        """
        wanted = [c.strip() for c in coins.split(",") if c.strip()] or None
        crypto, fx = await net.gather(life.crypto_prices(wanted), life.fx_rates())
        return life.describe_markets(crypto, fx)

    @mcp.tool()
    async def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
        """
        Convert an amount between two currencies at the current official rate.
        Example: convert 500 USD to NGN.
        """
        base = from_currency.strip().upper()
        target = to_currency.strip().upper()

        payload = await life.fx_rates(base)
        if not payload or not payload.get("rates"):
            return f"I couldn't fetch exchange rates for {base} right now."

        rate = payload["rates"].get(target)
        if rate is None:
            return f"I don't have a rate for {base} to {target}."

        converted = amount * rate
        return (
            f"{amount:,.2f} {base} = {converted:,.2f} {target}\n"
            f"Rate: 1 {base} = {rate:,.4f} {target} "
            f"(official/interbank, updated {payload.get('time_last_update_utc', 'recently')})"
        )

    @mcp.tool()
    async def get_prayer_times(city: str = "", country: str = "") -> str:
        """
        Islamic prayer times for today (Fajr, Sunrise, Dhuhr, Asr, Maghrib, Isha)
        along with the Hijri date. Defaults to the user's home city.
        """
        target_city = city.strip() or config.HOME_CITY
        target_country = country.strip() or config.HOME_COUNTRY
        payload = await life.prayer_times(target_city, target_country)
        if not payload:
            return f"I couldn't get prayer times for {target_city}, {target_country}."
        return life.describe_prayer_times(payload, target_city, target_country)
