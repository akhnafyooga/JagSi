# JagSi UI/UX and Figma prototype handoff

**Owner:** RafiBusthami. **Review:** Akhnaf for sensor and AI accuracy, Akmal for frontend feasibility and caregiver flows. **Deliverable:** an editable, connected mobile-first web prototype in a new Figma page, with desktop layouts and a walkthrough from the public landing to resolution of a simulated alert.

## Design from the caregiver’s task

Start with a blank canvas. Use the current repo and AI PRD to understand behavior and data. Establish a new visual system before laying out screens, with a type scale, spacing grid, surfaces, semantic colors, navigation, and component states. Use Inter and a restrained JagSi palette of indigo, lavender and warm neutrals. Reserve red for urgent events. Use Indonesian for caregiver-facing copy.

Use the [Wise homepage](https://wise.com/) and [GAMABANTU reference](https://www.figma.com/proto/KPJRbVHRgXNFJPGUcVcywO/Mokap--Copy-?node-id=4001-2279) as visual references. Carry over the principles of generous display typography, layered product previews, strong section transitions, and a focused call to action. Create original JagSi artwork and compositions. Show the product in use, with an illustrated watch, a readable caregiver dashboard preview, and a concrete alert example. Keep the app navigation at the top on mobile or in a desktop sidebar. A marketing footer can provide secondary links.

Design first at 390 px and at 1440 px, then check the 768 px layout. Provide 44 px touch targets, visible keyboard focus, text labels for status, and contrast of 4.5:1 for normal text and 3:1 for large text and essential control indicators. Use a short, purposeful hero transition to show a reading moving from watch to dashboard. Provide a static reduced-motion state and a pause affordance if motion loops. Display urgent events immediately.

## Screen inventory and prototype actions

| Surface | Questions and tasks to support |
| --- | --- |
| Public landing | Explain who JagSi supports, show the watch and app in use, walk through readings → summary → response, and open the dashboard. Include feature sections, an FAQ and a footer. |
| Beranda | Identify the monitored person and device, show last update and recent changes, read the model-backed summary, and open Monitoring, Riwayat or Darurat. Show the caregiver assistant entry with example questions and an unavailable state. |
| Monitoring | Read heart rate, SpO₂ and temperature with units, source and timestamp. Show connection and freshness states, fall monitor status and a path to the relevant trend or event. |
| Riwayat | Change the time range, inspect a reading and distinguish missing data from an actual measurement. Use available data for each series and visibly identify sample content. |
| Profil & perangkat | Check device connection, edit or inspect caregiver contacts, view medication reminders and set notification preferences. Show a disconnected device and an empty reminder list. |
| Darurat | Distinguish manual SOS, a possible ML-detected fall, and a firmware-rule alert where relevant. Open the event, see timestamp and source, reach the saved contact, acknowledge and verify the event in history. Acknowledgment records a response and does not confirm safety. |

Use reusable components for top navigation, metric cards, charts, data status, summary evidence, warnings, and contact actions. Include populated, loading, empty, error, stale or disconnected states where each applies. Use fictional people and clearly labeled simulated input throughout.

## Data walkthroughs

1. **Sensor to summary.** Start at the public landing, enter the app and select a demo device. Show the Wokwi watch sending readings through MQTT, the backend, and the cloud mirror. Follow one changed reading into Monitoring. In Beranda open the trend summary and show the observation period, sample count and supporting averages from the same 60-reading window. Include a variant for uncertain and stale analysis. The implemented dashboard pulls the owned model result from the progress endpoint.
2. **Fall or SOS to caregiver response.** Trigger a simulated motion event and show a possible fall with its source. Use a separate path for wearer-triggered SOS. Open Darurat, inspect the event, show the saved contact action, acknowledge it, and return to see the same event ID marked acknowledged. Demonstrate how active alerts remain visible during a vital-data outage.
3. **Summary to next action.** Link a changing trend to its evidence and a check-in action. If illustrating lifestyle or consumption guidance, use a fictional reviewed care plan and show why the instruction applies. Treat personal guidance and clinical warning rules as proposed. Sensor patterns alone do not determine diet, medication or diagnosis.
4. **Failure and recovery.** Enter a disconnected or stale state, show the last valid reading time, and replace the outdated trend claim. Resume the feed and show the new observation time. Include insufficient data, cloud/model unavailable, and a retry path.

## Delivery and sign-off

- Share the Figma page link, mobile and desktop prototype entry links, and a component/guidelines board with editable layers.
- Add a screen-to-data map showing sources, fields, states, and interaction destinations. Mark each interaction as backed by existing behavior, requiring implementation, or simulated only. Include the expected outcomes and data for the four walkthroughs.
- Ask Akhnaf and Akmal to run the prototype from the landing without narration. Confirm they can find the latest reading, trace a summary to its evidence, distinguish SOS from fall and verify acknowledgment in the log.
- Recheck 390, 768 and 1440 px for navigation, text wrapping, chart labels and prominent alert actions. Check every primary action and route back. Record unresolved issues with frame links and owners.

Use the [AI model PRD](ai-model-prd.md), [MQTT contract](mqtt-contract.md), [cloud inference contract](cloud-inference.md) and [backend handoff](handoff-rafibusthami.md) as technical references. Share the final prototype for design review before beginning frontend implementation.
