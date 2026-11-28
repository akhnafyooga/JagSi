# Prerequisites for the JagSi Wokwi stream and HTML controls

**Goal:** Start a repeatable randomized sensor stream from an HTML control panel and see it reach the existing JagSi app through its normal MQTT and backend flow. This document defines what must be in place before implementation.

## Choose the producer and control path

Use **Wokwi firmware as the only telemetry publisher for a Wokwi demo device**. Add a simulation mode that generates correlated virtual sensor inputs and uses the firmware's existing publish functions. Keep the physical sensor path as the default for hardware builds. The existing Python fake device can serve as a backend smoke test under a separate device ID. [Firmware guide](../firmware/jagsi-watch/README.md) · [Fake device](../tools/fake_device.py)

The proposed control path is **HTML button → demo controller → MQTT command → Wokwi firmware → MQTT telemetry → FastAPI → dashboard**. Define a simulation-only command and acknowledgment contract before creating the page. The browser sends the requested scenario to the controller. The controller validates the device, scenario and request, then publishes the command. Keep broker credentials server-side. Reuse the existing command transport where supported and verify that the Wokwi firmware subscribes to it. [MQTT contract](mqtt-contract.md)

## Required setup

| Layer | Prerequisite |
| --- | --- |
| Wokwi | A runnable JagSi watch project, working virtual Wi-Fi and a broker reachable from Wokwi. Confirm manual SOS still works. |
| MQTT | Use one agreed broker, topic prefix and device ID across firmware, backend and dashboard. Use an isolated demo namespace and account or a private test broker with a reachable gateway. |
| Backend | FastAPI accepts the existing telemetry and motion schemas. Establish baseline connectivity through the health endpoint and check that the fall classifier loads. For AI summary verification, start the cloud mirror and configure the trend artifact and Supabase or a labeled PostgreSQL stand-in. |
| Dashboard | Use the existing API base URL and select the same device ID. Confirm Monitoring can show a real MQTT-originated demo reading and distinguishes that stream from frontend sample data. |
| HTML controls | Start with **Start / Stop stream**, **Trigger trend**, **Trigger simulated fall** and **Trigger SOS**. Show pending and acknowledged states with a request ID, plus a timeout and retry path. Prevent duplicate start requests from creating overlapping producers. If controls are hosted, authorize access to the demo device. |

## Randomization requirements

**Default mode: vary the existing Wokwi readings within their current threshold bands.** Read the virtual sensor controls as the baseline and add small, correlated variation before publishing. Moving a Wokwi control changes the baseline. The HTML **Start / Stop** control enables or disables this variation. When disabled, firmware publishes the original virtual sensor values at the usual cadence.

- Use JagSi's existing warning boundaries and validation rules without changing them. For each channel, limit generated values to the baseline's current band. If a random step would cross a boundary, reflect it back into the permitted range. Check the rounded value that will actually be sent, since rounding near a boundary can change its classification.
- Keep bounded variation separate from explicit test scenarios. A caregiver can intentionally move a virtual sensor into a different band or use a scenario button to test a transition. Default variation should never inject a fall or SOS event.
- Verify baselines just below, exactly on, and just above each boundary. Run many seeded steps and check that the backend assigns every default-mode reading to the same band as its baseline while values still change wherever the band and sensor resolution allow it.

- Use a seed for replay and stateful variation between samples. Generate a baseline, gradual drift and small jitter. Pick scenario timing explicitly so the same seed and command sequence recreate a failure.
- Preserve existing payload fields, units, timestamps and simulation provenance. Publish vitals every two seconds and retain the firmware motion contract of 30 chronological samples at 10 Hz with a one-second hop. Preserve the cadence when switching scenarios.
- Begin with stable readings and one sustained single-channel trend. Allow about two minutes of valid data for the 60-reading trend window. Ordinary motion and a simulated impact use different motion sequences. Trigger SOS through the event path and identify its source separately from an ML fall.
- Record seed, device ID, command ID and time for each run. Randomization models signal behavior for testing and presentation. Accuracy on physical sensors requires separate evidence.

## Ready to build when

1. Wokwi produces an accepted MQTT reading and the dashboard shows the matching device and value.
2. The team agrees on the command and acknowledgment payloads and can trace one command to Wokwi. Acknowledgment should mean the firmware applied the request.
3. The team has expected results for stable data, a changing trend, manual SOS, a motion-model test and a stopped feed. For a simulated fall, capture whether inference actually generated the alert and its source.

After implementation, verify that **Start** produces a visible stream, repeating a seed reproduces the sample sequence, **Stop** produces stale status, and resuming restores fresh data. Check the event log after fall and SOS separately, including acknowledgment and refresh.
