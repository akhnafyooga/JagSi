# Demonstrating daily-brief input availability and quality

## Evidence for the AI Engineer role

JagSi checks two different properties. **Availability** asks whether the device supplied the needed fields in time. **Quality** asks whether the brief preserves what was supplied, communicates uncertainty and avoids unsupported recommendations. A successful response alone establishes neither.

The read-only audit of the local SQLite database found 25 simulated readings from one device. Heart rate, oxygen saturation and temperature were present in all 25, and all receive timestamps could be parsed. The median interval between consecutive records was 12 seconds. Fourteen of 24 intervals reached the dashboard’s 10-second freshness threshold, and the longest interval was 175 seconds. Session boundaries are unknown. These figures describe stored records; they cannot establish uptime, packet loss or physical sensor accuracy. [Aggregate snapshot](evidence/watch-input-coverage.json)

## Controlled input matrix

The benchmark uses a disposable SQLite database, a frozen clock, actual device-scoped retrieval and the trained local model worker. Each accepted request is replayed twice. The matrix crosses seven watch situations, seven lab profiles, three alert states and two collection-date states. Each JSONL record contains the inputs, response, source and a named Boolean per expectation. An assertion failure makes the command exit unsuccessfully. Six additional invalid inputs exercise the request schema. An ASGI regression test checks HTTP 422 and verifies inference is never invoked for them.

| Demonstration | Expected result |
| --- | --- |
| Watch absent, no reviewed labs | Disclose both missing sources. Give no lab-specific diet advice. |
| Fresh simulated high pulse | Keep the value and unit, identify the simulation, avoid treating it as a real observation. |
| Exactly 10 seconds since receipt | Mark the reading delayed; preserve its time. |
| Unparseable watch time | Explain the missing confirmed reading. Exclude the unverified numbers. |
| One missing vital | Preserve the available vital. Do not invent the other. |
| Report with a decimal comma, comparator or missing unit | Preserve the literal value. Explicitly identify an unconfirmed unit. |
| Reviewed LDL high and unresolved SOS | Give the alert and immediate action. Omit routine meal advice until the alert is acknowledged. |
| Unflagged LDL or low hemoglobin | Lab-specific food logic is restricted to a confirmed high-LDL flag. |
| Whitespace-only label, multiline label, excessive rows or invalid date | Reject the request before running the model. |

The independent cold replay loads the checkpoint in two separate processes. Each process decodes all 16 legal watch/alert/LDL combinations without a previously cached pattern. All 16 pairs matched exactly on this machine. Repeated caregiver requests additionally exercise the normal pattern cache with different values and dates. [Cold replay evidence](evidence/daily-brief-cold-replay.json)

## Measured results

The second full run passed all 4,038 checks across 294 accepted cases and six rejected cases. All 294 accepted responses identified the trained local adapter and matched their repeat exactly. The first run passed 4,036 checks: one first response used local rules and its repeat differed. Its evidence checks passed. The cause of that individual fallback was not captured. The backend now logs the exception class without logging wearer inputs. Keep both runs when presenting reliability. [First-run failure record](evidence/daily-brief-first-run-failures.json)

For a short, concrete demonstration, select bench-86 and bench-100 in the case file. Both use simulated heart rate 153 bpm and high LDL 142 mg/dL. The first gives routine guidance and the second has an open alert and gives the immediate action. Neither case has a confirmed collection date.

## Reproduce

Run from the repository root with the local adapter installed.

~~~powershell
.venv/Scripts/python backend/ml/audit_watch_coverage.py
.venv/Scripts/python backend/ml/benchmark_brief_inputs.py
.venv/Scripts/python backend/ml/check_brief_replay.py
~~~

For the presentation, show the stored-data snapshot first, then select two rows from the [case results](evidence/daily-brief-input-quality.jsonl) with the same lab values and different alert status. Show the food bullet giving way to the alert action. Finish with the two independent model runs. This demonstrates that relevant changes in evidence change the response while unchanged inputs produce stable output.

## Coverage boundaries

The matrix uses hand-specified, synthetic reviewed lab rows. It starts after OCR review. It tests evidence preservation and presentation; it supplies no population estimate for OCR, clinical interpretation, diet suitability or usability. The collection-date input belongs to one report. Multi-person report matching, source-document transcription audits across unseen labs, physical watch calibration and prospective device availability remain separate validation tasks. A fixed CPU replay establishes reproducibility for this checkpoint and environment.
