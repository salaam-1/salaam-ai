# Salaam — EVAL-002 Outcome Categories and Pass Rule

Prepared: 2026-09-15
Blacksmith task: **Define the outcome categories and the pass rule**
Project: `salaam-ai`
Branch: `feat/EVAL-002-define-outcome-categories-and-pass-rule`

## Purpose and evidence boundary

This document defines the judgment vocabulary for the EVAL-002 baseline and for later runs. It uses examples from the EVAL-001 failure landscape, but it does not turn self-run reproductions or incomplete evidence into qualifying real-use cases. The source category for each example remains visible so an independent reader can check the judgment.

A case must be written with its expected outcome category before its behavior is observed. The expected category is part of the case definition, not something chosen after seeing the result.

## Outcome categories

### 1. Handled well

**Plain-language definition:** The system understood the user's request, chose an appropriate response or tool path, produced an answer that satisfies the request, and did not hide a material limitation or error. If no tool fits, a direct answer or a clarifying question is the correct handling rather than a forced tool call.

**Failure-landscape example:** S01 records a local root request returning the expected Salaam frontend HTML with `HTTP/1.1 200 OK`. This is a control rather than an orchestration failure, but it is a concrete example of an expected behavior being completed successfully.

### 2. Handled badly

**Plain-language definition:** The system's user-visible behavior materially fails the request: it selects the wrong tool or route, uses a malformed argument, silently drops a required intent, returns an irrelevant result, gives no response, or hides a failure that prevents the user from getting what they asked for.

**Failure-landscape example:** FEC-01 records `What time is it in Lagos?` producing Nigeria news instead of the requested current time. The request was exact, the expected intent was clear, and the observed result was materially unrelated.

A partway failure is also handled badly when it ends in no useful response, silently drops the remaining request, or conceals the failure. FEC-04/V05 is an example of the last two concerns: the market portion was returned, while the Nigeria portion was silently dropped.

### 3. Degraded but acceptable

**Plain-language definition:** The system does not perform ideally, but it still gives the user a useful, truthful, and sufficiently safe result. The degradation is visible or honestly explained, the delivered portion remains correct, and the user can understand what was not completed or what to do next. Slowness, a clearly disclosed limitation, or a sensible partial result can qualify; a silent wrong answer cannot.

**Failure-landscape example:** S12 records a later voice run in which speech was transcribed and voice worked, but the observed symptom was that latency was too high. If the case's expected contract allows a delayed but otherwise correct response and the delay is disclosed or measured against that contract, this is degraded but acceptable rather than handled well. The evidence record does not preserve an exact latency measurement, so S12 is an example from the landscape, not a pre-approved pass for a future case.

For a tool failing partway, a useful and transparent partial result can be degraded but acceptable only when the remaining gap is explicitly stated and the partial result is correct. A silent omission is handled badly.

### 4. Unclear

**Plain-language definition:** The available evidence cannot support a reliable call among the other categories, or the behavior fits no category cleanly. Missing request/result data, missing traces, contradictory evidence with no resolvable explanation, and an unclassified combination belong here rather than being forced into a favorable or unfavorable category.

**Failure-landscape example:** S13 preserves the diagnostic request `Hello Salaam.` but not the resulting terminal output. Without the observed behavior, an independent reader cannot decide whether the interaction was handled well, badly, or degraded.

`Unclear` is an evidence judgment, not a soft pass.

## Awkward cases named by the sprint

| Situation | Handled well | Degraded but acceptable | Handled badly | Unclear |
|---|---|---|---|---|
| No tool chosen when none fits | A direct answer or clarifying question is given because no tool is appropriate. | The system gives a useful direct answer but explains a limitation or asks for one missing detail before continuing. | It forces an unrelated tool, invents a tool result, or silently fails to answer. | The trace does not show whether a tool was available, chosen, or needed. |
| A tool fails partway | The failure is avoided or fully recovered and the requested result is completed. | The failure is surfaced, any partial result is correct, and the remaining limitation or next step is explicit. | The user gets no useful response, a wrong result, or a silent omission after the failure. | The evidence does not show where the tool failed or what the user received. |
| Two tools return results that disagree | The system reconciles the results using a stated, checkable rule and gives the consistent answer. | The disagreement is disclosed, the system gives a bounded result or asks the user to choose, and it does not present an unresolved result as certain. | It silently selects one result, combines incompatible results, or presents a contradiction as settled fact. | The evidence shows disagreement but not which tools ran, what they returned, or how the result was produced. |
| Several tools or intents are combined | Every required intent is handled, with each result attributable and consistent. | Some intents are handled correctly and the missing part is explicitly disclosed with a useful next step. | One or more required intents are silently dropped, or tool outputs are mixed into a misleading answer. | The trace is too incomplete to establish which intents or tools were handled. |

The EVAL-001 record currently states that wrong-tool use, no-tool use when none fits, partway tool failure, two tools disagreeing, and several tools combined were not genuinely observed in recoverable real usage (apart from fresh self-run diagnostics that are explicitly not qualifying incidents). That statement is preserved as an evidence boundary; the examples above define how future real cases will be judged and do not claim those categories were already observed.

## Frozen pass rule

**Frozen on 2026-09-15, before any EVAL-002 baseline case is written:**

A case passes exactly when the observed behavior matches the case's pre-written expected outcome category under the definitions in this document, using the evidence recorded for that case. An independent reader must be able to reach the same category from the preserved original request or trigger, expected behavior, actual behavior, source/session, and rationale. A case does not pass merely because the system did something useful; it must satisfy the category that was fixed for that case.

The expected category, acceptance conditions, and evidence fields are frozen when the case is authored. They cannot be changed after observing the run to make the baseline pass. If the behavior fits no category cleanly, or the evidence is insufficient to distinguish categories, it is recorded as **unclear** and counts as **not passing**. An unclear result is never re-judged later merely because a later result looks better or makes a different category convenient.

For a case expected to be `degraded but acceptable`, the run passes only if the documented degradation contract is met: the useful portion is correct, the limitation is surfaced, and the user is not misled about what remains incomplete. For a case expected to be `handled badly`, the run is not a success baseline merely because the failure was reproduced; it passes only if the case definition explicitly says the evaluation target is to detect or classify that failure. The case record must therefore state whether its expected category describes desired product behavior or a failure-classification target.

## Required case record

Every baseline case should preserve these fields before running it:

1. Case ID and date authored.
2. Original user request or trigger, in the user's own words when available.
3. Source/session/incident.
4. Expected outcome category and the concrete conditions for that category.
5. Relevant tools or routes that are expected to run, if any.
6. Actual behavior and raw output sufficient for an independent reader.
7. Final category, pass/fail result, and a short rationale tied to this frozen rule.

This structure prevents a missing trace or a convenient reinterpretation from becoming a pass after the fact.

## Freeze statement

This vocabulary and pass rule are frozen as of **2026-09-15** for the EVAL-002 baseline. Any later change requires a new dated version and must not retroactively re-judge cases already written or run under this version.
