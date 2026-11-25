# Presenting JagSi’s AI | Five-minute walkthrough

**Presenter:** Akhnaf, AI engineer. **Audience:** project assessors and teammates. **Evidence baseline:** commit `3cd3d10`. Use the [technical report](ai-technical-report.md) for citations and exact results.

| Time | Slide and visual | Speaker notes |
| --- | --- | --- |
| 0:00–0:35 | **What can the caregiver see?** Show the summary card from a verified run, or a clearly labeled example. | “Our question was whether a caregiver could see what changed and check the readings behind the statement. JagSi uses one model for sudden movement and another for changes over roughly two minutes.” |
| 0:35–1:25 | **How we trained the models.** Show two rows: 30 motion samples → fall classifier, and 60 vital readings → trend classifier. | “We trained both Random Forests in Python. The fall model learns features around an impact, including tilt and inactivity. The trend model learns how three channels vary across a window. We kept simulated subjects or complete sessions together when splitting the data.” |
| 1:25–2:20 | **Where the models struggle.** Display 24/24 falls detected alongside 94 false alerts at the stored threshold. Show the noisy-stable results as 36 stable, 23 rising, 41 uncertain. | “Detecting every scripted fall sounds impressive until you count false alarms. Deliberate lying down remained difficult even after raising the threshold. The trend model also confused extra noise with a rising pulse. Those two failures guide our next training run.” |
| 2:20–4:15 | **Trace one summary.** Follow the demonstration below. | “The trend label comes from our trained model. The sentence uses measurements from the same window. When the feed becomes stale, the dashboard removes the previous conclusion.” |
| 4:15–5:00 | **What is ready?** Show the automated checks, scope of the live evidence and one next experiment. | “The frontend and model suites passed. These models were evaluated on simulated sessions. Our next test is to replay independently scripted noisy and ordinary movements and measure both missed events and false alarms.” State the hosted-demo status observed at rehearsal. |

## Demo cues

1. **Before presenting**, allow roughly two minutes for 60 readings to accumulate. Ask Rafi to keep the selected device’s progress response visible and Akmal to open the home screen. Record the candidate SHA, model version and whether the database is hosted or local.
2. **Show the evidence.** On a ready response, point to the label, observation end time and first/last group averages. Read the corresponding Indonesian summary and identify the same numbers on screen. If the model returns uncertain, show that outcome as observed.
3. **Stop the feed.** Wait for the API to report stale and the card to refresh. Explain why the earlier trend disappears. A fall or SOS demonstration is a separate event flow. If showing one, identify its recorded source.
4. **If the live path is unavailable**, show a dated, verified recording if available. Otherwise use the saved evaluation tables and a labeled example from the [AI PRD](ai-model-prd.md). State which segments were simulated, replayed or live.

## Likely assessor questions

- **Did the team train the AI that writes the summary?** The team trained the classifier that determines the trend. The app turns that output and the measured averages into Indonesian text. The chat feature uses a separate service.
- **Does a score of 1.00 mean the system is accurate on people?** The 1.00 macro-F1 came from 150 synthetic sessions generated in the same way as the training data. The noise experiment shows performance changes under different conditions.
- **Can JagSi recommend a diet or predict illness?** The implemented card describes short-term sensor patterns. The product plan reserves individual care instructions for reviewed care plans. The current evaluations measure trend recognition and scripted falls.
