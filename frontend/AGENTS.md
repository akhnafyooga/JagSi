# JagSi frontend design rules

These rules apply throughout the Next.js App Router frontend. Use TypeScript, React, Tailwind 3 utilities and the Material 3 palette in `tailwind.config.ts`. Global styles live in `app/globals.css`.

## Structure and spacing

- Make the caregiver’s next decision easy to find. Group each reading with its label, unit, time and status. Give active alerts priority over routine summaries.
- Use a descriptive page heading and ordered section headings. Give each section one primary action when an action is needed. Keep supporting text short and in the interface’s language.
- Prefer the Tailwind spacing scale: 2 for related items, 3–4 within cards, 4–6 between groups. Align section edges and baselines. Use Inter with weight and size to distinguish headings, readings and metadata.
- Preserve the shared 430px dashboard shell unless the task changes the layout. Coordinate wider layouts with BottomNav, overlays and the main content padding. Check that fixed navigation clears the final action.

## Visual restraint and reuse

- Reuse VitalCard, StatusBanner, TrendChart, Icon, BottomNav and the existing alert components where their semantics fit. Keep shared behavior in its existing owner. Use token pairs such as surface/on-surface and primary/on-primary.
- Avoid unrequested neon gradients, glass effects, stacked shadows, nested cards, decorative badges and filler copy. Use spacing or a surface change before adding elevation. Reserve error color for meaningful alerts or failures.
- For dynamic views implement loading, empty, error and populated states. For live readings also show stale, disconnected and simulated states as applicable. Keep dates, units and provenance visible. Provide keyboard focus and appropriate hover, pressed and disabled feedback on controls.

## Responsive and accessible acceptance

- Inspect the rendered route at 390, 768 and 1440 CSS pixels wide. Check wrapping, chart labels, long Indonesian text, overlays and bottom navigation. Prevent horizontal page scrolling and clipped controls.
- Use native buttons, links, labels and landmarks. Name icon-only actions. Keep tab order logical, focus visible, and focus restoration predictable after a dialog. Communicate status using text alongside color. Respect reduced motion.
- Check actual foreground/background combinations: at least 4.5:1 for normal text, 3:1 for large text and essential control boundaries or indicators. Aim for 44px touch targets. Test keyboard activation and the primary action on the rendered page.
- For visual work, inspect before/after renders and exercise relevant states. Vitest/jsdom covers behavior; use a real browser for layout, focus and responsive evidence.

## Figma implementation and visual verification

- Treat the exact Figma frame as the source of truth when asked to slice or implement a design. Inspect the matching mobile and desktop frames before editing. Record the frame links and dimensions.
- Reproduce the frame's section order, composition, typography, spacing, assets, and control placement. Keep the app wired to real data and existing actions. When a required control has no design, design it in Figma first and link that frame.
- Capture the running app at the frame's exact viewport dimensions. Compare the full page and key sections side by side with Figma. Fix material differences in hierarchy, placement, sizing, and styling before claiming fidelity. A passing interaction test or an overflow check only verifies that specific behavior.
- Include the Figma frame links and actual browser screenshots in the handoff. Call out intentional differences and any viewport or state you could not verify. If Figma is inaccessible, report the blocker before claiming any visual match.
