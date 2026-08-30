"""
Salaam -- LiveKit voice agent.

Listens on your microphone, reasons with an LLM, speaks back, and pulls every
tool from the Salaam MCP server in real time.

Start the MCP server FIRST:
    python main.py server

Then, in a second terminal:
    python main.py voice-dev
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import sys

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    TurnHandlingOptions,
    cli,
    inference,
    mcp,
    room_io,
)

from salaam.config import config
from salaam.persona import GREETING, system_prompt

# Plugin imports MUST happen here, at module scope on the main thread.
# LiveKit registers plugins on import, and registration from a job thread
# raises "Plugins must be registered on the main thread" — which kills the job
# the instant it starts, so the worker looks registered but never joins a room.
try:
    from livekit.plugins import groq as groq_plugin
except ImportError:
    groq_plugin = None
try:
    from livekit.plugins import google as google_plugin
except ImportError:
    google_plugin = None
try:
    from livekit.plugins import silero as silero_plugin
except ImportError:
    silero_plugin = None

load_dotenv()

# The Windows console defaults to cp1252, which raises UnicodeEncodeError on
# any non-ASCII character — enough to kill the agent before it starts. Force
# UTF-8 so a stray arrow or dash in a log line can never take the process down.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

logger = logging.getLogger("salaam")

# --- Pipeline choices ------------------------------------------------------
# SALAAM_PIPELINE picks where speech and reasoning actually run:
#
#   "livekit"  STT/LLM/TTS through LiveKit Inference. No extra keys, but it
#              draws on LiveKit credits -- and when they run out the STT socket
#              returns 429 and the whole session dies mid-conversation.
#   "gemini"   Google's Gemini Live realtime model: one free AI Studio key
#              (no payment card) handles listening, thinking and speaking.
#
# Default to gemini when a Google key is present, since that's the setup that
# keeps working once LiveKit's free inference allowance is gone.
#   "groq"     Groq Whisper for hearing + Groq Orpheus for speaking, with
#              Google Gemini doing the thinking. Both keys are free and
#              card-less, and Groq is the fastest inference available -- which
#              is also the answer to "why is it slow".
# NOTE: `os.getenv(name, default)` returns "" -- not the default -- when the key
# exists in .env but is blank, which is exactly how the file ships. Use `or` so
# a blank value falls through to the auto-pick.
PIPELINE = (
    os.getenv("SALAAM_PIPELINE")
    or ("groq" if os.getenv("GROQ_API_KEY") else "livekit")
).strip().lower()

STT_MODEL = os.getenv("SALAAM_STT", "deepgram/nova-3")
LLM_MODEL = os.getenv("SALAAM_LLM", "openai/gpt-5.3-chat-latest")
TTS_MODEL = os.getenv("SALAAM_TTS", "cartesia/sonic-3")
TTS_VOICE = os.getenv("SALAAM_TTS_VOICE", "9626c31c-bec5-4cca-baa8-f8ba9e84c8bc")
GROQ_STT = os.getenv("SALAAM_GROQ_STT", "whisper-large-v3-turbo")
GROQ_TTS = os.getenv("SALAAM_GROQ_TTS", "canopylabs/orpheus-v1-english")
GROQ_VOICE = os.getenv("SALAAM_GROQ_VOICE", "autumn")
GROQ_LLM = os.getenv("SALAAM_GROQ_LLM", "llama-3.3-70b-versatile")
GEMINI_MODEL = os.getenv("SALAAM_GEMINI_MODEL", "gemini-2.5-flash")

# Nova-3 keyterm prompting. Generic English models mangle Nigerian names and
# finance vocabulary -- "naira" becomes "Nyra", "Tinubu" becomes "to new boo".
# Boosting them costs nothing and sharply improves transcription accuracy.
KEYTERMS = [
    "Salaam",
    # Places
    "Nigeria", "Lagos", "Abuja", "Kano", "Ibadan", "Kaduna", "Port Harcourt",
    "Enugu", "Benin City", "Borno", "Benue", "Niger Delta",
    # Money and institutions
    "naira", "kobo", "CBN", "Central Bank of Nigeria", "NNPC", "EFCC", "NDDC",
    "INEC", "NAFDAC", "forex", "NAFEM", "subsidy",
    # People and companies commonly discussed
    "Tinubu", "Dangote", "Aliko Dangote", "BUA", "Zenith Bank", "GTBank",
    "Access Bank", "Flutterwave", "Paystack", "MTN", "Glo", "Airtel",
    # Media
    "Punch", "Vanguard", "Channels Television", "Premium Times", "Nairametrics",
    # Religion and greetings
    "Fajr", "Dhuhr", "Asr", "Maghrib", "Isha", "Hijri", "Ramadan",
]


def mcp_url() -> str:
    """Where the Salaam MCP server is listening.

    Under WSL, 127.0.0.1 points at the Linux VM rather than the Windows host
    running the server, so resolve the host IP from the default route.
    """
    explicit = os.getenv("SALAAM_MCP_URL")
    if explicit:
        return explicit

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = os.getenv("MCP_PORT", "8000")

    if platform.system() == "Linux" and "microsoft" in platform.release().lower():
        try:
            route = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=3,
            ).stdout.split()
            host = route[route.index("via") + 1]
        except Exception:
            logger.warning("Couldn't resolve the WSL host IP; falling back to %s", host)

    return f"http://{host}:{port}/sse"


class SalaamAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=system_prompt(voice=True))

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions=GREETING, allow_interruptions=True
        )


server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    """Load the VAD once per worker instead of once per conversation.

    Without this the first thing a caller experiences is the model loading,
    which is a big chunk of the delay before the greeting.
    """
    if PIPELINE == "groq" and silero_plugin is not None:
        proc.userdata["vad"] = silero_plugin.VAD.load()


server.setup_fnc = prewarm


# No agent_name on purpose. Setting one switches LiveKit to *explicit* dispatch:
# the worker registers fine but never joins a room until something calls the
# AgentDispatchService. With it omitted, Salaam is dispatched automatically to
# any new room -- which is what the Agents Playground and a plain web client
# expect. Only add a name if you're driving dispatch yourself (e.g. telephony).
@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    url = mcp_url()
    logger.info("Salaam connecting to MCP server at %s", url)

    if PIPELINE == "groq":
        # Llama on Groq does the reasoning by default. Groq answers in about a
        # second and is already proven by the STT path, so keeping the whole
        # pipeline on one provider removes a moving part.
        #
        # Gemini is opt-in via SALAAM_LLM_PROVIDER=google, because AI Studio
        # retires model names without warning — gemini-2.5-flash now returns
        # 404 "no longer available to new users" on freshly created keys, which
        # surfaces only as an LLM timeout mid-conversation.
        if os.getenv("SALAAM_LLM_PROVIDER", "").lower() == "google" and google_plugin:
            brain = google_plugin.LLM(
                model=GEMINI_MODEL, api_key=os.getenv("GOOGLE_API_KEY")
            )
            brain_name = GEMINI_MODEL
        else:
            brain = groq_plugin.LLM(model=GROQ_LLM)
            brain_name = GROQ_LLM

        logger.info("Pipeline: Groq (%s / %s / %s)", GROQ_STT, brain_name, GROQ_TTS)
        parts = dict(
            stt=groq_plugin.STT(model=GROQ_STT, language="en"),
            llm=brain,
            tts=groq_plugin.TTS(model=GROQ_TTS, voice=GROQ_VOICE),
            # Silero runs locally, and 'vad' turn detection avoids the
            # inference gateway entirely -- which matters because VAD and
            # turn detection are quota-metered there too.
            # Silero benchmarks at ~52x realtime on this hardware, so if you
            # ever see "inference is slower than realtime" with a delay that
            # keeps growing, the model is not the problem — the machine is out
            # of RAM and the process is stalling on page faults. Close things.
            vad=ctx.proc.userdata.get("vad") or silero_plugin.VAD.load(),
            turn_handling=TurnHandlingOptions(turn_detection="vad"),
        )
    else:
        logger.info("Pipeline: LiveKit Inference (%s / %s / %s)", STT_MODEL, LLM_MODEL, TTS_MODEL)
        parts = dict(
            stt=inference.STT(
                model=STT_MODEL,
                language="en",
                extra_kwargs={"keyterm": KEYTERMS},
            ),
            llm=inference.LLM(model=LLM_MODEL),
            tts=inference.TTS(model=TTS_MODEL, voice=TTS_VOICE, language="en"),
            # Voice activity and end-of-turn detection both run server-side.
            # The old livekit.plugins.silero / turn_detector path is deprecated
            # and spawns a local ONNX inference subprocess that hangs on Windows
            # before the worker ever registers.
            vad=inference.VAD(),
            turn_handling=TurnHandlingOptions(turn_detection=inference.TurnDetector()),
        )

    session = AgentSession(
        **parts,
        preemptive_generation=True,
        # Every tool on the MCP server -- news, web, weather, markets, memory --
        # is discovered here at startup. The generous session timeout matters:
        # get_daily_briefing fans out to ~16 feeds plus three APIs, which
        # comfortably exceeds the 5s default.
        mcp_servers=[
            mcp.MCPServerHTTP(
                url=url,
                transport_type="sse",
                timeout=10,
                client_session_timeout_seconds=60,
            )
        ],
    )

    # A 429 from the inference gateway kills the session with a stack trace
    # buried in debug logs, and from the user's side it just looks like a
    # broken assistant. Say plainly what happened and what fixes it.
    @session.on("error")
    def _on_error(event) -> None:
        detail = str(getattr(event, "error", event))
        if "terms acceptance" in detail.lower():
            logger.error(
                "\n"
                "  " + "-" * 60 + "\n"
                "  Groq needs you to accept the terms for the voice model.\n"
                "  Salaam can hear and think, but not speak, until you do.\n\n"
                "  One click:\n"
                "    https://console.groq.com/playground?model="
                "canopylabs%2Forpheus-v1-english\n"
                "    -> press Accept, then restart: python main.py voice-dev\n"
                "  " + "-" * 60
            )
        elif "429" in detail or "Too Many Requests" in detail:
            logger.error(
                "\n"
                "  " + "-" * 60 + "\n"
                "  LiveKit Inference quota is exhausted (HTTP 429).\n"
                "  Salaam can join a room but cannot hear or speak.\n\n"
                "  Fix, free and without a payment card:\n"
                "    1. Get a key at https://console.groq.com/keys\n"
                "    2. Put GROQ_API_KEY=gsk_... in .env\n"
                "    3. Restart:  python main.py voice-dev\n"
                "  " + "-" * 60
            )
        else:
            logger.error("Session error: %s", detail)

    await session.start(
        agent=SalaamAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(),
    )


def check_memory() -> None:
    """Warn when the machine is too memory-starved to sustain a conversation.

    Voice is realtime: the VAD has to keep pace with the audio stream. Silero
    benchmarks around 50x realtime, so it never falls behind on its own — but
    under heavy paging the process simply stops getting scheduled, the VAD lag
    grows without bound, and the assistant answers once and then goes quiet.
    That reads exactly like a broken pipeline, so name it here instead.
    """
    try:
        import psutil
    except ImportError:
        return

    memory = psutil.virtual_memory()
    free_gb = memory.available / 1e9
    if free_gb >= 2.0:
        return

    hogs = {}
    for proc in psutil.process_iter(["name", "memory_info"]):
        try:
            name = proc.info["name"] or "?"
            hogs[name] = hogs.get(name, 0) + proc.info["memory_info"].rss
        except Exception:
            continue
    worst = sorted(hogs.items(), key=lambda kv: -kv[1])[:4]

    print(
        "\n  " + "-" * 64 + "\n"
        f"  LOW MEMORY: only {free_gb:.1f} GB free ({memory.percent:.0f}% used).\n\n"
        "  Voice needs realtime processing. Below about 2 GB free, Windows\n"
        "  pages heavily, the voice-activity detector falls behind, and Salaam\n"
        "  will answer once and then go silent. That is not a bug in Salaam --\n"
        "  it is the machine running out of room.\n\n"
        "  Biggest consumers right now:\n"
        + "".join(f"    {name:<24} {rss / 1e6:>7.0f} MB\n" for name, rss in worst)
        + "\n  Close a browser (they are usually the worst) and restart.\n"
        "  " + "-" * 64
    )


def preflight() -> None:
    """Refuse to start quietly in a state that cannot possibly work.

    The LiveKit pipeline fails *after* the agent has joined a room -- it looks
    connected, then dies on the first word. Better to say so up front.
    """
    check_memory()
    if PIPELINE == "groq":
        if not os.getenv("GROQ_API_KEY"):
            print(
                "\n  GROQ_API_KEY is empty but SALAAM_PIPELINE=groq.\n"
                "  Get a free key (no card): https://console.groq.com/keys\n"
            )
            sys.exit(1)
        missing = [
            name
            for name, mod in (("livekit-plugins-groq", groq_plugin),
                              ("livekit-plugins-silero", silero_plugin))
            if mod is None
        ]
        if missing:
            print(f"\n  Missing plugins: {', '.join(missing)}\n"
                  f"  Install with: pip install {' '.join(missing)}\n")
            sys.exit(1)
        google = os.getenv("SALAAM_LLM_PROVIDER", "").lower() == "google"
        brain = GEMINI_MODEL if (google and google_plugin) else GROQ_LLM
        print(f"\n  Salaam voice -- Groq Whisper -> {brain} -> Groq Orpheus\n")
        return

    # ASCII only: the Windows console is cp1252 and box-drawing characters
    # raise UnicodeEncodeError, which would crash the agent at startup.
    print(
        "\n"
        "  " + "-" * 64 + "\n"
        "  WARNING: running on LiveKit Inference.\n"
        "\n"
        "  If your LiveKit credits are used up, this pipeline fails in a way\n"
        "  that looks like a bug: the agent joins the room and publishes\n"
        "  audio, then dies with HTTP 429 the moment you speak. You hear\n"
        "  nothing and no error is shown in the browser.\n"
        "\n"
        "  Free fix, no payment card:\n"
        "    1. https://console.groq.com/keys  ->  create a key\n"
        "    2. Put GROQ_API_KEY=gsk_... in .env\n"
        "    3. Restart: python main.py voice-dev\n"
        "  " + "-" * 64 + "\n"
    )


def main() -> None:
    preflight()
    cli.run_app(server)


def dev() -> None:
    """Entry point for `salaam_voice` -- injects the `dev` subcommand."""
    if len(sys.argv) == 1:
        sys.argv.append("dev")
    main()


if __name__ == "__main__":
    main()
