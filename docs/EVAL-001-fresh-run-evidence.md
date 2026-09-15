# EVAL-001 Fresh Run Evidence

## FEC-01 — Current-time request routed incorrectly

- Date: 15 Sep 2026
- Observed page time: 01:32
- Request: `What time is it in Lagos?`
- Expected: A current time for Lagos.
- Actual: The application displayed `NEWS: "WHAT TIME IS IT IN LAGOS?"` and returned Nigeria news results instead of the requested time.
- Evidence source: Local Salaam web app at `http://127.0.0.1:8080`
- Run type: Fresh reproduction during EVAL-001 recovery.
- Router source: `webapp.html` — no current-time route; unmatched requests fall through to `get_news_about`.

### Observed output

NEWS: "WHAT TIME IS IT IN LAGOS?" (last 7d, NG)

As of 15 Sep 2026, 01:32

Billionaire Dangote launches oil refinery 'people's IPO', Africa's biggest — Reuters · 4h ago

Why the Lagos-Calabar coastal highway, By Eric Teniola — Premium Times Nigeria · 5h ago

Lagos To Cut Olusosun Waste With New Transfer Stations – Hamzat — TVC News · 7h ago

Nigerian billionaire Dangote launches oil refinery IPO, Africa's biggest share sale — CNBC Africa · 8h ago

NPFL: Sporting Lagos Claims Lagos Derby Bragging Rights — Voice of Nigeria · 15h ago

Lagos Coastal Road: Concerns over alleged feud between FG, state officials — The Guardian Nigeria News · 20h ago

Man drowns in Lagos river after alleged cultist chase — Punch Newspapers · 1d ago

NPFL: Sporting Lagos too strong for Inter Lagos — ACLSports · 1d ago

Conclusion: The exact request was reproduced and the observed result did not satisfy the requested current-time intent.

---

## FEC-02 — Weather request passed malformed city value

- Date: 15 Sep 2026
- Request: `What is the weather in Kano?`
- Expected: Weather information for Kano.
- Actual: The application displayed `I couldn't find weather data for "Kano?". Try a nearby larger city.`
- Evidence source: Local Salaam web app at `http://127.0.0.1:8080`
- Run type: Fresh reproduction during EVAL-001 recovery.
- Router source: `webapp.html` — the weather branch extracts the text after `weather`, leaving the trailing `?` in the city value.

### Observed output

I couldn't find weather data for "Kano?". Try a nearby larger city.

Conclusion: The exact request was reproduced and the weather route passed an incorrect city value, causing the request to fail instead of returning Kano weather.

---

## FEC-03 — Latest Nigeria headlines fell through to generic news routing

- Date: 15 Sep 2026
- Observed page time: 01:38
- Request: `latest Nigeria headlines`
- Expected: The dedicated Nigeria-headlines/news route.
- Actual: The application displayed `NEWS: "LATEST NIGERIA HEADLINES"` and returned a generic news result set.
- Evidence source: Local Salaam web app at `http://127.0.0.1:8080`
- Run type: Fresh reproduction during EVAL-001 recovery.
- Router source: `webapp.html` — the dedicated Nigeria-news branch requires `nigeria|nigerian|lagos|abuja` **and** the word `news`. `latest Nigeria headlines` does not contain `news`, so it reaches the final `get_news_about` fallback.

### Observed output

NEWS: "LATEST NIGERIA HEADLINES" (last 7d, NG)

As of 15 Sep 2026, 01:38

Nigeria’s $1 Trillion Dream And The Great Corporate Exodus — newtimes.com.ng · 5h ago

Seun Kuti shares controversial take on Nigerian beggars — PM News Nigeria · 13h ago

Falconets Hammer New Caledonia 10-1, Advance To Round Of 16 — News Agency of Nigeria · 1d ago

Tinubu Creates New Welfare Fund For Armed Forces Personnel, Donates His Salaries From June 2023 — THISDAYLIVE · 2d ago

Transfer Centre LIVE! Football transfer news, updates and rumours — Sky Sports · 3d ago

Documentary alert Mambilla: A Dam Of Broken Promises Airing Date: Sunday, 13th September, 2026 Time: 7:30PM Showing on Trust TV, StarTimes 164. You can also livestream on Youtube and other platforms below. #trusttvnews #Mambilla #Dam — instagram.com · 3d ago

Police arrest woman filmed using sex toys on minor — Premium Times Nigeria · 3d ago

Latest News on African Business, Economy, Startups & Venture Capital — WeeTracker · 3d ago

Conclusion: The exact request was reproduced. The application returned news, but the request did not use the dedicated Nigeria-news routing path and instead fell through to the generic `get_news_about` route.

---

## FEC-04 / V05 — Combined request satisfied only the market intent

- Date: 15 Sep 2026
- Request: `What is happening in Nigeria and what is Bitcoin doing?`
- Expected: The application should address both parts of the request: Nigeria-related information and Bitcoin/market information.
- Actual: The application displayed the Markets view with Bitcoin, Ethereum, Binancecoin, Ripple, Solana, and currency data, but did not provide the requested Nigeria-related information.
- Evidence source: Local Salaam web app at `http://127.0.0.1:8080`
- Run type: Fresh reproduction during EVAL-001 recovery.
- Router source: `webapp.html` — the market branch matches `bitcoin` and returns `get_markets`, so the combined Nigeria intent is not handled separately.

### Observed output

### Markets

**Crypto (USD)**

Binancecoin: $718.98 ▲ +0.07% (24h)

Bitcoin: $78,000.00 ▲ +1.68% (24h)

Ethereum: $2,513.89 ▲ +1.36% (24h)

Ripple: $1.42 ▲ +5.45% (24h)

Solana: $102.64 ▲ +3.09% (24h)

**Currency (1 USD)**

NGN: 1,326.47

EUR: 0.87

GBP: 0.74

GHS: 11.50

ZAR: 16.25

KES: 129.44

Conclusion: The exact combined request was reproduced. The application handled the Bitcoin/market portion but dropped the Nigeria portion instead of satisfying both intents.
