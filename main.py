import argparse
import sys

# Launcher target → the LiveKit CLI subcommand it maps onto.
VOICE_TARGETS = {
    "voice": "start",
    "voice-dev": "dev",
    # Pre-downloads the Silero VAD and turn-detector model weights. Without
    # this the first `voice-dev` run stalls on "initializing process" while it
    # fetches a few hundred MB in the background with no progress output.
    "download": "download-files",
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Salaam launcher",
        epilog="Run 'download' once before the first 'voice-dev'.",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="server",
        choices=["server", *VOICE_TARGETS],
        help="What to run. Defaults to 'server'.",
    )
    # Anything after the target (e.g. --transport stdio) belongs to the
    # subcommand, not to this launcher.
    args, passthrough = parser.parse_known_args()

    if args.target == "server":
        from server import main as server_main

        server_main(passthrough)
        return

    from agent_salaam import main as voice_main

    sys.argv = [sys.argv[0], VOICE_TARGETS[args.target], *passthrough]
    voice_main()


if __name__ == "__main__":
    main()
