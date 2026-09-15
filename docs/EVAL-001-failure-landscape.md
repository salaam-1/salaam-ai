# Salaam — Blacksmith EVAL-001 Failure-Landscape Ledger

Prepared: 2026-09-14
Blacksmith task: **Reconstruct the failure landscape from real usage**
Project: `salaam-ai`
Branch: `feat/EVAL-001-reconstruct-the-failure-landscape-from-real-usage`

## Scope and evidence rule

The Blacksmith task requires a written starting list of at least 15 situations from real usage. A situation qualifies only when the available evidence preserves the user's request or trigger, expected behavior, actual behavior, a specific source/session/incident, and the original wording or note behind it.

This ledger deliberately distinguishes qualifying situations from controls, historical incidents, hypotheses, diagnostics without preserved results, and candidates. Those categories are retained because they are useful evidence, but they are not counted toward the 15 qualifying situations unless the evidence supports all required fields.

The available source material is primarily the `Publish Salaam Safely` debugging conversation, supplemented by `Assess GitHub Access` for the reported orchestration problem. The available record contains terminal output, browser status, pasted code, and incident notes. It does not preserve enough exact tool-orchestration runs to claim that the 15-situation acceptance criterion is currently satisfied.

### Evidence categories

- `confirmed`: directly observed in the available conversation evidence;
- `control`: real-use evidence showing that a component worked, not a failure;
- `documented-historical`: a previously recorded failure mode preserved in pasted code/comments;
- `hypothesis`: a proposed cause, not established evidence;
- `candidate`: a real reported pattern lacking an exact request/result pair;
- `proposed-no-result`: a diagnostic that was suggested but whose result is not preserved;
- `excluded`: retained with a reason because it does not qualify for the evaluation set.

## Blacksmith acceptance criteria

1. At least 15 qualifying situations from real usage, each with the user's request, expected behavior, and actual behavior.
2. Each situation names a specific session, conversation, or documented incident.
3. Coverage of wrong-tool use, no tool when none fits, partway tool failure, conflicting tools, and several tools combined — or an explicit statement that a category was not genuinely observed.
4. Situations judged not worth testing remain listed with their exclusion reason.
5. The original quote or note behind each situation remains alongside it.

The task outcome is raw material for the evaluation set, not necessarily the final evaluation set.

## Evidence sources

- **Publish Salaam Safely** — the main voice-debugging conversation, including browser state, terminal commands, code, and incident notes.
- **Assess GitHub Access** — contains the reported Salaam tool-selection/orchestration problem and the plan to recover exact incidents.
- **Managed AI Agents Building** — architectural context, but no exact Salaam failure run currently preserved.

## Starting evidence inventory

| ID | Original request or trigger | Expected behavior | Actual behavior / evidence | Source | Category | Qualification |
|---|---|---|---|---|---|---|
| S01 | `curl.exe -i http://127.0.0.1:10000` | The local Salaam root route should return the frontend HTML. | `HTTP/1.1 200 OK`, Uvicorn, content length 31218, and Salaam HTML were returned. | Publish Salaam Safely; pasted PowerShell output. | Control | Keep as control; does not count toward 15. |
| S02 | `Invoke-WebRequest http://localhost:8080` | The local server check should complete safely. | PowerShell displayed a script-execution safety warning and the operation was cancelled. | Publish Salaam Safely; pasted PowerShell interaction. | Excluded | PowerShell tooling interruption, not a Salaam failure. |
| S03 | `Invoke-WebRequest http://localhost:8080 -UseBasicParsing` | The server on port 8080 should return the Salaam page. | `StatusCode: 200`, `StatusDescription: OK`, Uvicorn response and 31218 bytes of HTML were returned. | Publish Salaam Safely; pasted PowerShell output. | Control | Keep as control; does not count toward 15. |
| S04 | Starting `python main.py voice-dev` | The voice worker should start with the configured STT, LLM, and TTS pipeline. | Plugins registered, HTTP listener opened, and LiveKit worker registered in EU West B. | Publish Salaam Safely; pasted terminal output. | Control | Keep as control; startup succeeded but downstream behavior remained unresolved. |
| S05 | Starting the worker in deprecated development mode | The launcher should start the worker or clearly report compatibility. | Worker started but emitted deprecation and removed-hot-reload warnings. | Publish Salaam Safely; pasted worker output. | Control / warning | Keep as control; not the target failure. |
| S06 | Browser voice setup before speaking | SDK, token, microphone, room, agent, audio stream, and playback should initialize. | `Voice SDK loaded`, `Access token`, `Microphone`, `Room connected`, `Salaam joined`, `Audio stream`, and `Sound playing — via audio engine` appeared. | Publish Salaam Safely; copied browser status. | Control | Keep as control; does not count toward 15. |
| S07 | `Hello.` | Salaam should recognize the utterance, complete the turn, generate an answer, and speak it. | The browser displayed the utterance. No assistant response is shown in the preserved record. | Publish Salaam Safely; room `salaam-bf24db14`, agent `AJ_LPSxEw5verp8`. | Confirmed | Qualifying voice incident. |
| S08 | `Briefly.` | Salaam should return a short spoken answer. | The browser displayed the utterance, but the session record says `NO RESPONSE`. | Publish Salaam Safely; same correlated voice session. | Confirmed | Qualifying voice incident. |
| S09 | `Brief me.` | Salaam should begin a brief spoken response. | The browser displayed the utterance, but the session record says `NO RESPONSE`. | Publish Salaam Safely; same correlated voice session. | Confirmed | Qualifying voice incident. |
| S11 | Speaking while the voice worker showed only `registered worker` | The worker should emit post-registration STT, turn, LLM, TTS, or error activity. | The conversation reports no visible post-registration activity in the terminal. The raw terminal output is not preserved. | Publish Salaam Safely; terminal diagnosis. | Confirmed report / incomplete raw log | Retain as evidence, but distinguish the reported observation from the missing raw log. |
| S12 | `Hello.` and `How are you doing?` in a later run | Salaam should answer promptly after speech is transcribed. | Speech was transcribed, but the interaction was described as `voice works, but latency is too high`. Exact delay was not recorded. | Publish Salaam Safely; room `salaam-b0ce158d`, agent `AJ_wqJaXusFnuKf`. | Confirmed symptom | Qualifying symptom, with latency measurement absent. |
| S13 | `Hello Salaam.` as a controlled diagnostic | The terminal should show STT, turn, LLM, TTS, error, or timeout activity after speech. | The requested diagnostic is preserved, but no resulting terminal output is preserved. | Publish Salaam Safely; diagnostic instruction. | Proposed-no-result | Excluded until the result is recovered. |
| S14 | `Say hello.` latency test | The response delay should be measured and classified. | The test was proposed, but no measured duration or result is preserved. | Publish Salaam Safely; diagnostic instruction. | Proposed-no-result | Excluded until the result is recovered. |
| S15 | Browser agent readiness check during cold worker startup | The UI should not report the agent as absent while the worker is still booting. | The repository comment records: `// and warning at 12s produced a false "no agent" line seconds before it` followed by `// actually arrived.` The code then waits 30 seconds before logging `No agent joined after 30s. Start it: python main.py voice-dev`. | `webapp.html` around lines 615–621; repository source. | Documented-historical | Retain as historical evidence; not a current-run voice incident. |
| S16 | Browser audio after subscribing to the remote WebRTC track | A subscribed track should be audible and available to the visualizer. | Pasted frontend comments document a prior Chrome silence bug caused by routing the track into an audio context without also attaching it to a media element. | Publish Salaam Safely; pasted frontend code/comment. | Documented-historical | Retain as historical evidence; current run showed audio-engine playback. |
| S17 | Voice session using the LiveKit inference path | Inference should continue without exhausting quota or silently killing the session. | Pasted code documents a prior `429` failure mode in which the inference gateway kills the session and the user experiences a broken assistant. | Publish Salaam Safely; code comment/error handler. | Documented-historical | Retain as historical evidence; not observed in the current run. |
| S18 | A normal request requiring one of Salaam's tools | Salaam should select and invoke the correct tool, or explain why no tool applies. | The user reported that individual tools work but Salaam sometimes chooses the wrong tool or does not use a tool when it should. No exact request/result pair is preserved in the available evidence. | Assess GitHub Access; user-reported project history. | Candidate | Does not yet qualify; exact request, expected result, actual result, and source wording must be recovered. |

## Evidence count and gap

The inventory contains controls, exclusions, historical incidents, confirmed voice incidents, and an orchestration candidate. It does **not** currently establish 15 qualifying situations under the acceptance criterion.

The strongest directly evidenced qualifying material is concentrated in the voice pipeline:

- S07–S09 are three distinct utterances from one voice session with preserved requests and no-response outcomes.
- S11 records a reported lack of post-registration terminal activity, but the raw terminal output is not preserved.
- S12 records a later latency symptom with exact utterances but no measured delay.

The remaining rows are controls, diagnostics without preserved results, historical frontend/provider failures, or an orchestration candidate without an exact request/result pair.

This is an evidence gap, not a reason to invent additional incidents.

## Tool-orchestration evidence gap

EVAL-001 is intended to establish the failure landscape for Salaam's orchestration behavior. The currently recovered material is heavily weighted toward the voice pipeline: **16 of the 17 current inventory rows are voice/startup/frontend/provider evidence, while the only orchestration-specific row is S18 and it lacks an exact request/result pair.**

The current ledger therefore does not yet provide enough real orchestration incidents to build a defensible orchestration baseline.

The correct next step is to recover exact historical orchestration examples from the available project history or, if they cannot be recovered, document that limitation and use newly observed real usage rather than fabricating examples.

## Required category coverage

- **Wrong tool used:** now supported by fresh evidence in FEC-01, FEC-02, B04, and V05, each with an exact request and observed result.
- **No tool used when none fits:** not genuinely observed in the available evidence. Do not fabricate one.
- **Tool failing partway:** not genuinely observed in the available evidence. Do not fabricate one.
- **Two tools disagreeing:** not genuinely observed in the available evidence. Do not fabricate one.
- **Several tools combined:** Salaam has a multi-tool architecture, but no real multi-tool failure run is preserved. Architecture alone is not an incident.


## Fresh evidence recovered after initial review

A bounded fresh-evidence pass recovered four distinct Console/application-router failures that were not represented in the original S01-S18 inventory:

- **FEC-01 — Current-time request routed incorrectly:** `What time is it in Lagos?` did not reach a current-time route. A repeat returned news instead of the requested time. The current `webapp.html` routing does not contain a current-time route and unmatched requests fall through to `get_news_about`.
- **FEC-02 — Weather request handled incorrectly:** `What is the weather in Kano?` passed the question text as the city value and returned no weather result.
- **B04 — Latest Nigeria headlines routed to the wrong result:** `latest Nigeria headlines` fell through to a Wikipedia-style summary instead of returning current Nigeria headlines.
- **V05 — Combined intent was partially dropped:** `What is happening in Nigeria and what is Bitcoin doing?` selected the markets path because `bitcoin` was present and silently dropped the Nigeria-news intent.

These are distinct observed router/application failures from fresh runs. They are stronger evidence for the orchestration failure landscape than the earlier S18 candidate because each has an exact request and observed result.

Historical recovery also confirmed two voice incidents:

- **H01 — No-response voice session:** the historical session contained `Hello.`, `Briefly.`, and `Brief me.` and produced no confirmed assistant response.
- **H02 — Voice latency symptom:** a later historical run contained `Hello.` and `How are you doing?`; speech was transcribed and voice worked, but the observed result was that latency was too high. No exact latency measurement was preserved.

The recovered evidence therefore strengthens the failure landscape, but it still does **not** establish 15 qualifying situations. The ledger deliberately keeps the evidence ceiling explicit rather than counting duplicate symptoms, controls, hypotheses, or unrecoverable historical claims as separate incidents.
## Main confirmed failure pattern

The strongest confirmed voice pattern is:

`browser microphone / room connection → Salaam joins → user utterance appears → no confirmed assistant response`

The evidence does not establish whether the dead point is:

- agent-side STT delivery;
- VAD or end-of-turn detection;
- LLM invocation or response handling;
- TTS generation;
- audio publication; or
- provider/quota failure.

Possible causes mentioned in the conversation include Silero VAD, local memory pressure, Llama 3.3 70B latency, Orpheus TTS, and LiveKit `429` quota errors. These remain hypotheses or historical failure modes unless tied to a specific run log.

## What this ledger establishes

1. Several real voice failures/symptoms are preserved with their original requests and observed outcomes.
2. Controls show that the local server, worker startup, room connection, and browser audio setup could succeed in the relevant runs.
3. Historical frontend and provider failure modes are preserved separately from current-run evidence.
4. Fresh Console/application-router runs now provide exact request/result evidence for several orchestration failures, including incorrect routing, malformed parameter handling, wrong-result fallback, and partial intent dropping.
5. The currently available evidence is insufficient to claim that the 15-situation acceptance criterion has been met.

The next step should use the recovered orchestration failures as the starting point for the baseline, while keeping the 15-situation evidence gap explicit rather than padding the ledger with controls, duplicates, or hypotheses.
