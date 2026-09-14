# Salaam — Blacksmith EVAL-001 Failure-Landscape Ledger

Prepared: 2026-09-14
Blacksmith task: **Reconstruct the failure landscape from real usage**
Project: `salaam-ai`
Branch: `feat/EVAL-001-reconstruct-the-failure-landscape-from-real-usage`

## Scope and evidence rule

The logged-in Blacksmith task requires a written starting list of at least 15 situations from real usage. It does not require 15 independent incidents. Multiple situations may come from one session or conversation when each is meaningfully distinct and has its own request or trigger, expected behavior, actual behavior, source, and original wording.

The source ChatGPT conversation exposes pasted terminal output, code, browser status, screenshots, and diagnostic notes. It does not expose a separate downloadable ZIP in the browser view. This ledger therefore uses the embedded records currently available; no second upload is required for this pass.

The categories below are marked carefully:

- `confirmed`: directly observed in the conversation evidence;
- `control`: real-use evidence showing that a component worked, not a failure;
- `documented-historical`: a previously recorded failure mode in pasted code/comments;
- `hypothesis`: a proposed cause, not established evidence;
- `candidate`: a real reported pattern lacking an exact request/result pair;
- `proposed-no-result`: a diagnostic that was suggested but whose result is not preserved;
- `excluded`: retained because Blacksmith requires excluded situations to remain listed with a reason.

## Blacksmith acceptance criteria confirmed

1. At least 15 situations from real usage, each with the user's request, expected behavior, and actual behavior.
2. Each situation names a specific session, conversation, or documented incident.
3. Coverage of wrong-tool use, no tool when none fits, partway tool failure, conflicting tools, and several tools combined—or an explicit statement that a category was not genuinely observed.
4. Situations judged not worth testing remain listed with their exclusion reason.
5. The original quote or note behind each situation remains alongside it.

The task outcome is a written starting list for the evaluation set, not necessarily the final evaluation set itself.

## Evidence sources

- **Publish Salaam Safely** — the main voice-debugging conversation, with browser state, terminal commands, code, logs, and incident notes.
- **Assess GitHub Access** — the competition framing conversation, including the reported tool-selection problem and the plan to recover real incidents.
- **Managed AI Agents Building** — architectural context about safety, observability, approvals, and managed-agent operation; not currently a source of exact Salaam failure runs.

## Starting list of 18 real-use situations

| ID | Original request or trigger | Expected behavior | Actual behavior / evidence | Source | Category | Status / decision |
|---|---|---|---|---|---|---|
| S01 | `curl.exe -i http://127.0.0.1:10000` | The local Salaam root route should return the frontend HTML. | `HTTP/1.1 200 OK`, Uvicorn, content length 31218, HTML title `Salaam`. | Publish Salaam Safely; user-pasted PowerShell output. | Server/frontend control | Control-confirmed; keep as a control, not a failure. |
| S02 | `Invoke-WebRequest http://localhost:8080` | The local server check should complete safely. | PowerShell displayed a script-execution safety warning and the operation was cancelled. | Publish Salaam Safely; user-pasted/quoted PowerShell interaction. | Tooling interruption | Excluded from agent evaluation; this was a PowerShell safety prompt, not a Salaam failure. |
| S03 | `Invoke-WebRequest http://localhost:8080 -UseBasicParsing` | The server on port 8080 should return the Salaam page. | `StatusCode: 200`, `StatusDescription: OK`, Uvicorn response and 31218 bytes of HTML. | Publish Salaam Safely; user-pasted PowerShell output. | Server/frontend control | Control-confirmed; keep as a control, not a failure. |
| S04 | Starting `python main.py voice-dev` | The voice worker should start with the configured STT, LLM, and TTS pipeline. | Plugins registered, HTTP listener opened, and LiveKit worker registered in EU West B. | Publish Salaam Safely; user-pasted terminal output. | Voice-worker startup control | Control-confirmed; startup succeeded but downstream behavior remained unresolved. |
| S05 | Starting the worker in the deprecated development mode | The launcher should still start the worker or clearly report compatibility. | Worker started but emitted deprecation and removed-hot-reload warnings. | Publish Salaam Safely; user-pasted worker output. | Compatibility warning | Confirmed non-blocking condition; not the current failure. |
| S06 | Browser voice setup before speaking | SDK, token, microphone, room, agent, audio stream, and playback should initialize. | `Voice SDK loaded`, `Access token`, `Microphone`, `Room connected`, `Salaam joined`, `Audio stream`, and `Sound playing — via audio engine` all appeared. | Publish Salaam Safely; browser status copied into the conversation. | Voice connection control | Control-confirmed; rules out a basic connection/setup explanation for this run. |
| S07 | `Hello.` | Salaam should recognize the utterance, complete the turn, generate an answer, and speak it. | The browser displayed the user utterance. No assistant response is shown. | Publish Salaam Safely; room `salaam-bf24db14`, agent `AJ_LPSxEw5verp8`. | Speech-input / response boundary | Confirmed; include. |
| S08 | `Briefly.` | Salaam should return a short spoken answer. | The browser displayed the utterance, but the session record says `NO RESPONSE`. | Publish Salaam Safely; same correlated voice session. | No spoken response | Confirmed; include. |
| S09 | `Brief me.` | Salaam should begin a brief spoken response. | The browser displayed the utterance, but the session record says `NO RESPONSE`. | Publish Salaam Safely; same correlated voice session. | No spoken response | Confirmed; include. |
| S10 | The complete turn after `Hello`, `Briefly`, and `Brief me` | After user speech reaches the transcript display, the worker should produce LLM/TTS output or a visible error. | Browser connection and user transcripts succeeded, but no spoken or displayed assistant response was produced. | Publish Salaam Safely; same correlated session. | Core voice pipeline failure | Confirmed system-level situation; include. |
| S11 | Speaking while the voice worker shows only `registered worker` | The worker should emit post-registration STT, turn, LLM, TTS, or error activity. | The conversation states that the terminal showed no activity after worker registration. | Publish Salaam Safely; terminal diagnosis. | Missing observability | Reported in the conversation; include with a note that the raw post-speech terminal output is not preserved. |
| S12 | `Hello.` and `How are you doing?` in a later run | Salaam should answer promptly after speech is transcribed. | Speech was transcribed, but the interaction was described as “voice works, but latency is too high.” | Publish Salaam Safely; room `salaam-b0ce158d`, agent `AJ_wqJaXusFnuKf`. | Excessive latency | Confirmed symptom; include, but exact delay must remain `not recorded`. |
| S13 | `Hello Salaam.` as a controlled diagnostic | The terminal should show STT, turn, LLM, TTS, error, or timeout activity after speech. | The transcript preserves the requested test but no resulting terminal output. | Publish Salaam Safely; diagnostic instruction. | Proposed diagnostic | Excluded from observed-failure count until a result is recovered. |
| S14 | `Say hello.` latency test | The response delay should be measured and classified as fast, acceptable, slow, or very slow. | The test was proposed, but no measured duration or result is preserved. | Publish Salaam Safely; diagnostic instruction. | Proposed diagnostic | Excluded from observed-failure count; retained with reason. |
| S15 | Browser agent warning before a cold worker finishes starting | The UI should not report the agent as absent while the worker is still booting. | Pasted frontend comments document a prior false `no agent` warning around 12 seconds before the agent arrived; timeout was increased to 30 seconds. | Publish Salaam Safely; developer comment in pasted frontend code. | Misleading readiness signal | Documented historical incident; include as a prior real-use situation, clearly separate from the current no-response run. |
| S16 | Browser audio after subscribing to the remote WebRTC track | A subscribed track should be audible and available to the visualizer. | Pasted frontend comments document a prior Chrome silence bug caused by routing the track into an audio context without also attaching it to a media element. | Publish Salaam Safely; developer comment in pasted frontend code. | Historical browser-audio failure | Documented historical incident; retain but mark excluded from the current run because current status showed audio-engine playback. |
| S17 | Voice session using the LiveKit inference path | Inference should continue without exhausting quota or silently killing the session. | Pasted code documents a prior `429` failure mode in which the inference gateway kills the session and the user experiences a broken assistant. | Publish Salaam Safely; code comment and error handler. | Provider quota / session termination | Documented failure mode, not observed in the current run; candidate until original 429 logs are recovered. |
| S18 | A normal request requiring one of Salaam’s tools | Salaam should select and invoke the correct tool, or explain why no tool applies. | The user reports that individual tools work but Salaam sometimes chooses the wrong tool or does not use a tool when it should. | Assess GitHub Access; user-reported project history. | Orchestration / tool selection | Candidate; exact request/result pair still needed. |

## Required category coverage

- **Wrong tool used:** reported as a real Salaam pattern in S18, but no exact request/result pair is currently preserved. Keep as a candidate until the exact wording is recovered.
- **No tool used when none fits:** not observed in the available evidence. State this explicitly; do not fabricate one.
- **Tool failing partway:** not observed in the available evidence. State this explicitly; do not fabricate one.
- **Two tools disagreeing:** not observed in the available evidence. State this explicitly; do not fabricate one.
- **Several tools combined:** Salaam has a multi-tool architecture, but no real multi-tool failure run is preserved. State this explicitly; do not claim architecture alone is an incident.

## Main failure hypothesis, kept separate from evidence

The strongest confirmed pattern is:

`browser microphone / room connection → Salaam joins → user utterance appears → no confirmed assistant response`

The evidence does not yet establish whether the dead point is:

- agent-side STT delivery;
- VAD or end-of-turn detection;
- LLM invocation or response handling;
- TTS generation;
- audio publication; or
- provider/quota failure.

Possible causes mentioned in the conversation include Silero VAD, local memory pressure, Llama 3.3 70B latency, Orpheus TTS, and LiveKit `429` quota errors. These remain hypotheses or historical failure modes unless tied to a specific run log.

## Current readiness

This ledger now contains more than 15 documented situations and preserves controls, exclusions, historical incidents, hypotheses, and candidates instead of silently dropping them. Before opening the pull request, the candidate and category statements should be reviewed against the exact Blacksmith wording and, where possible, linked to the original ChatGPT message or pasted log location.

No code has been changed and no pull request has been opened yet.
