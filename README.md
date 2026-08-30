# Salaam

### A Personal AI Assistant for Voice, Intelligence & Real-Time Information

> **Salaam** is a personal AI assistant I built to bring conversational AI, voice interaction, real-time information, memory, and practical tools into one place.

Salaam can retrieve Nigerian and world news, search the web, check weather and prayer times, monitor markets, verify claims, remember information, manage reminders, and perform other tasks through a tool-based AI architecture.

The project is primarily designed for **personal use**. The repository is public so others can explore the engineering, architecture, and ideas behind it.

---

## ✨ Why I Built Salaam

I wanted an AI assistant that felt less like a chatbot and more like an assistant I could actually use throughout the day.

Salaam was inspired by an AI-assistant project I encountered online. I initially experimented with extending that implementation, but after running into architectural and implementation issues, I eventually rebuilt Salaam from the ground up and began shaping it around my own needs.

The result is a personal assistant combining:

- Conversational AI
- Voice interaction
- Real-time information retrieval
- Tool-based AI actions
- Persistent memory
- News aggregation
- Personal utilities
- A custom browser interface

The goal is not to build another generic chatbot. The goal is to build **an assistant that is genuinely useful in everyday life**.

---

## 🚀 What Salaam Can Do

### 🎙️ Voice Assistant

Talk to Salaam through the browser. The voice agent can listen, reason, call tools, and respond conversationally.

The voice stack is built around LiveKit Agents and supports configurable inference pipelines.

### 📰 News Intelligence

Salaam can retrieve and organize current information from Nigerian and international sources.

Capabilities include:

- Nigerian news
- World news
- Topic-based news search
- Category headlines
- Trending topics
- Daily briefings
- Parallel feed fetching
- Duplicate-story reduction
- Source-aware ranking

Example requests:

```text
What's happening in Nigeria today?
What's the latest on the naira?
Give me the latest news about AI.
What's trending in Nigeria?
```

### ✅ Claim Verification

Salaam can investigate claims and report how well they are corroborated by available reporting.

The verification system is deliberately cautious: it does not claim to directly observe reality.

It can classify coverage as:

- `WIDELY_REPORTED`
- `SOME_COVERAGE`
- `SINGLE_SOURCE`
- `NO_COVERAGE`

No coverage means **unverified**, not automatically false.

The system also attempts to detect syndicated reporting so that many copies of one story are not incorrectly treated as many independent confirmations.

### 🌐 Web Intelligence

Tools include:

- Web search
- URL fetching
- Wikipedia summaries
- URL opening
- World-monitor access

### 🌦️ Everyday Information

Salaam can retrieve:

- Weather
- Cryptocurrency and market information
- Currency exchange rates
- Prayer times

### 🧠 Persistent Memory

Salaam includes tools for remembering, recalling, saving, listing, and forgetting information.

Persistent data is stored locally under the configured Salaam data directory, which defaults to `~/.salaam`.

### ⏰ Reminders

Reminder tools allow Salaam to:

- Add reminders
- List reminders
- Complete reminders
- Retrieve due reminders

### 🖥️ System & Utility Tools

The tool layer also includes utilities for:

- Current time
- System information
- System status
- Opening applications
- Calculations
- JSON formatting
- Word counting

### 💼 Musa

Musa is an experimental business-assistant component providing tools for:

- Business profiles
- Listing search
- Drafting replies

---

## 🧩 Tool Architecture

Salaam currently exposes **56 MCP tools** across several modules.

```text
salaam/
├── tools/
│   ├── system.py
│   ├── web.py
│   ├── news.py
│   ├── life.py
│   ├── utils.py
│   ├── memory.py
│   ├── musa.py
│   └── verify.py
```

The model can select specialized tools instead of relying entirely on generated knowledge.

---

## 🏗️ Architecture

Salaam is built around two cooperating application layers:

```text
                         Salaam
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
        MCP Server                    Voice Agent
              │                           │
              ▼                           ▼
         56 Tools                    LiveKit Agents
              │                           │
              └─────────────┬─────────────┘
                            │
                            ▼
                External APIs / Data Sources
```

### MCP Server

The MCP server exposes Salaam's tools through FastMCP. It handles capabilities such as news, verification, web search, weather, markets, memory, reminders, system utilities, and more.

### Voice Agent

The voice agent uses LiveKit Agents to:

1. Receive voice input
2. Process the request
3. Reason with the configured model
4. Discover and call Salaam's MCP tools
5. Produce a spoken response

The tool layer is separated from the voice interface so that the server can also be used independently.

---

## 🖥️ Browser Interface

Salaam includes a browser interface with two main experiences.

### Console

The Console provides quick access to common capabilities including:

- Daily briefing
- Nigerian news
- Trending topics
- Markets
- Weather
- Prayer times
- Topic news
- Claim verification

It also accepts natural-language requests and routes them to the appropriate tool.

### Voice

The Voice interface allows Salaam to be used conversationally from a browser with microphone access and the configured LiveKit voice stack.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Agent framework | LiveKit Agents |
| Tool protocol | Model Context Protocol (MCP) / FastMCP |
| Browser UI | HTML / CSS / JavaScript |
| HTTP | httpx |
| Configuration | python-dotenv |
| Local system information | psutil |
| Persistent storage | JSON files |
| News | RSS / web sources |
| Weather | Open-Meteo |
| Markets / FX | External public APIs |
| Prayer times | AlAdhan |

Voice dependencies are optional; the base project can run without installing the voice extra.

---

## 📁 Project Structure

```text
salaam-assistant/
│
├── server.py              # MCP server entry point
├── agent_salaam.py        # Voice agent
├── webapp.py              # Browser UI server
├── webapp.html            # Browser interface
├── try_salaam.py          # Terminal console
├── main.py                # Application launcher
├── pyproject.toml         # Python project configuration
├── .env.example           # Safe configuration template
├── .gitignore             # Public repository exclusions
│
├── salaam/
│   ├── config.py          # Configuration and environment variables
│   ├── persona.py         # Assistant persona
│   ├── net.py             # Shared network helpers
│   ├── news.py            # News fetching, parsing and ranking
│   ├── life.py            # Weather, markets, FX and prayer times
│   ├── store.py           # Persistent JSON storage
│   ├── verify.py          # Claim verification
│   │
│   ├── tools/             # MCP tools
│   ├── prompts/           # Reusable prompts
│   ├── resources/         # MCP resources
│   └── musa/              # Business assistant
│
└── tests/                 # Offline test suite
```

---

## ⚙️ Installation

### Requirements

- Python 3.11 or newer
- Internet access for live information tools
- Voice credentials only if using the voice experience

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/salaam-ai.git
cd salaam-ai
```

### 2. Create a virtual environment

#### Windows

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

#### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Salaam

```bash
pip install -e .
```

For voice support:

```bash
pip install -e ".[voice]"
```

---

## 🔐 Configuration & Secrets

Copy the example configuration to a local `.env` file:

```bash
cp .env.example .env
```

On Windows PowerShell, you can copy it with:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` with your own values.

**Never commit `.env` to GitHub.**

The repository intentionally contains `.env.example` instead of real credentials.

---

## 🌐 Run the Browser Console

Start the browser application:

```bash
python webapp.py
```

Then open:

```text
http://127.0.0.1:8080
```

The Console does not require the voice stack.

---

## 🎙️ Run Voice Mode

Start the MCP server:

```bash
python main.py server
```

Then, in another terminal, start the development voice agent:

```bash
python main.py voice-dev
```

The voice experience requires the relevant LiveKit configuration in `.env`.

For production deployment, the MCP URL and other service endpoints should be configured through environment variables rather than hard-coded localhost addresses.

---

## 💻 Terminal Mode

Run the interactive terminal console:

```bash
python try_salaam.py
```

Or run a briefing directly:

```bash
python try_salaam.py brief
```

Example commands:

```text
salaam> brief
salaam> ng
salaam> trending
salaam> weather Kano
salaam> news dangote
salaam> markets
salaam> help
```

---

## 🧪 Testing

Salaam currently has **70 automated offline tests**.

Run them with:

```bash
python -m unittest discover -s tests
```

The tests cover areas including:

- Feed parsing
- News ranking
- News deduplication
- Source diversity
- Claim verification
- Syndication detection
- Persistent storage
- Utility behavior
- Web behavior
- Musa functionality

The test suite is designed to run without requiring live network access.

---

## 🗞️ News Reliability

Salaam fetches information from multiple external sources and attempts to degrade gracefully when individual sources fail.

News is fetched concurrently, processed, deduplicated, and ranked so that a slow or unavailable feed does not unnecessarily stop the rest of a briefing.

Search providers can throttle automated requests, so fallback behavior and short-lived caching are used where appropriate.

---

## 🎯 Design Principles

### Tools over hallucination

When current information is required, Salaam should retrieve it instead of pretending that the model already knows it.

### Attribution over false certainty

The assistant should distinguish between what sources report and what can actually be established.

### Verification is not omniscience

The claim-verification system evaluates available reporting and corroboration. It cannot directly observe reality.

Therefore:

```text
No coverage ≠ False
```

Instead:

```text
No coverage = Unverified
```

### Graceful failure

External services fail, feeds disappear, APIs throttle requests, and networks go down. Salaam is designed so that one failure should not unnecessarily bring down the whole assistant.

### Personal usefulness

Salaam is built around real-world personal use rather than being a generic chatbot demonstration.

---

## ⚠️ Current Limitations

Salaam is an actively developed personal project.

Some capabilities remain experimental and may occasionally produce incomplete or unsuccessful responses.

Known limitations include:

- External APIs and feeds can become unavailable.
- Search providers may throttle automated requests.
- News sources vary in reliability.
- Voice functionality depends on external services.
- Some tools require network access.
- Verification quality depends on available reporting.
- Persistent storage is currently file-based.
- The assistant's capabilities are still evolving.

---

## 🗺️ Roadmap

### Current

- [x] Conversational AI
- [x] Voice interaction
- [x] MCP tool architecture
- [x] Nigerian news
- [x] World news
- [x] Topic-based news
- [x] Trending information
- [x] Daily briefing
- [x] Claim verification
- [x] Web search
- [x] Weather
- [x] Markets
- [x] Currency conversion
- [x] Prayer times
- [x] Persistent memory
- [x] Reminders
- [x] Browser interface
- [x] Terminal interface
- [x] Offline test suite

### Planned

- [ ] Cloud deployment for personal access
- [ ] Improved mobile experience
- [ ] More robust long-term memory
- [ ] Additional personal automation
- [ ] Improved web-search reliability
- [ ] More tools and integrations
- [ ] Continued voice improvements

---

## 📸 Screenshots

Add screenshots of the current interface here as the project evolves.

Recommended sections:

- Console
- Voice assistant
- Daily briefing
- News / intelligence interface

---

## 🧑‍💻 What I Learned Building Salaam

Building Salaam has been an exploration of:

- AI agent design
- Tool calling
- Model Context Protocol (MCP)
- Voice AI
- Real-time information retrieval
- API integration
- News aggregation
- Data deduplication
- Source attribution
- Claim verification
- Persistent storage
- Web application development
- Python application architecture
- Automated testing
- Error handling
- Environment and secret management

The project has also been an exercise in taking an initial idea and turning it into a larger system with multiple independent components working together.

---

## 🔒 Project Status

**Personal project — actively developed**

Salaam is primarily built for my own use.

The repository is public to document the project, share the engineering work, and make the development process visible.

The hosted version is intended to remain a **private personal assistant rather than a public AI service**.

---

## 📄 License

This repository currently declares the MIT License in `pyproject.toml`.

Before the first public release, confirm that the current implementation and all retained dependencies/code are compatible with that license.

---

## 👤 About

Salaam is a personal project built while exploring AI agents, voice interfaces, tool-based architectures, real-time information systems, and practical AI applications.

The project was inspired by an existing AI-assistant project, but the current implementation was rebuilt and iterated around my own architecture, interface, tools, and use cases.

> **Build things you actually want to use.**
