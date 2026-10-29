# Wireframes part 2

Assumption: part 2 uses the same desktop card style and tokens as [wireframes-part-1.md](wireframes-part-1.md); onboarding step 3 opens the separate blink-monitor consent panel.

## Dashboard

`screensense/docs/wireframes-part-2.md` — dashboard layout

```text
┌──────────────────────────────────────────────────────────────┐
│ ScreenSense                                      [Settings]   │
│ Today                                                        │
│                                                              │
│  ┌──────────────────┐  ┌───────────────────┐                 │
│  │   (score ring)   │  │ Today's timeline  │                 │
│  │       78         │  │ active · breaks   │                 │
│  │ Wellness score  │  │ [hourly activity] │                 │
│  └──────────────────┘  └───────────────────┘                 │
│                                                              │
│  ┌──────────────────┐  ┌───────────────────┐                 │
│  │ Streak           │  │ 7-day trend       │                 │
│  │ 4 days            │  │ [score chart]      │                 │
│  └──────────────────┘  └───────────────────┘                 │
│                                                              │
│  Insight: You took 3 breaks today. Nice work.                │
└──────────────────────────────────────────────────────────────┘
```

**Components:** Today heading; wellness score ring with number and band label; today's activity timeline; streak card; 7-day score chart; one short insight. Support a 7-day and 30-day chart range if available. Always label charts and pair color with text or symbols.

**States and copy:**

- **Default:** show today's values, streak, 7-day chart, and a brief supportive insight; never call the wellness score a health or medical score.
- **Hover/focus:** cards gain a subtle surface emphasis; chart points expose date and value on focus as well as hover.
- **Empty:** for a new user, show `Your day starts here. A short break is a good first step.` and `Start a quick break`.
- **Error:** if local data cannot load, show `Your dashboard couldn't load. Please try again.` with `Retry`; do not show fabricated zeros.

**Keyboard and accessibility:** use a logical heading order and Tab order: Settings, score, timeline, streak, chart range/data, insight action. Charts have text summaries and keyboard-accessible data points. Screen readers hear the wellness score number and band, streak length, and chart range. Maintain WCAG AA contrast, visible focus, scalable text and layout, and labels in addition to color.

## Settings

`screensense/docs/wireframes-part-2.md` — settings layout

```text
┌──────────────────────────────────────────────────────────────┐
│ Settings                                          [Close]     │
│                                                              │
│ Breaks                                                       │
│ Work interval       [ 20 ] minutes                           │
│ Quick break         [ 20 ] seconds                           │
│ Work hours          [ Start ] to [ End ]                      │
│                                                              │
│ Context                                                      │
│ App rules           [ Manage allow / deny list ]              │
│                                                              │
│ Privacy                                                      │
│ Blink monitoring    [ Off ]  [ Learn about consent ]          │
│ Local data          [ Export ]  [ Delete all data ]           │
│                                                              │
│ Appearance       Theme [ System ▾ ]                           │
│ About            ScreenSense supports healthy screen habits. │
│                  It is not a medical device and does not      │
│                  diagnose or treat any condition.             │
│                                           [ Save changes ]    │
└──────────────────────────────────────────────────────────────┘
```

**Components:** grouped Breaks, Context, Privacy, Appearance, and About sections. Break interval supports 10–60 minutes (default 20); quick break supports 10–60 seconds (default 20). Work hours use local time. Context opens the app allow/deny rules. Privacy exposes blink-monitor opt-in, export, and delete-all. Theme follows the system by default. Include the full disclaimer in About: `ScreenSense supports healthy screen habits. It is not a medical device and does not diagnose or treat any condition.`

**States and copy:**

- **Default:** show saved values and `Save changes` disabled until a value changes.
- **Hover/focus:** controls show a visible focus ring; hover never changes a value. Tooltips clarify units and do not contain essential information unavailable elsewhere.
- **Empty:** if no context rules exist, show `No app rules yet. ScreenSense will use its default context settings.`
- **Error:** invalid interval or break length shows `Enter a value within the range shown.` Preserve the last saved value and keep the field focused. Save failure shows `Settings couldn't be saved. Your previous settings are still in place.`

**Keyboard and accessibility:** Tab and Shift+Tab follow the visual order; arrow keys operate radio groups and dropdowns; numeric fields support direct entry and announced units. Save and destructive actions are keyboard reachable. Delete-all requires a clearly labeled confirmation with Cancel as the initial focus. Associate every field with a label and range, announce validation errors, and support screen readers, high contrast, visible focus, and 100–150% scaling.

## Onboarding (three steps)

`screensense/docs/wireframes-part-2.md` — onboarding step 1 of 3

```text
┌────────────────────────────────────────────────┐
│ ScreenSense                         Step 1 of 3 │
│                                                │
│        Small breaks for screen-time balance    │
│                                                │
│  Your settings and activity stay on this       │
│  device. No account is needed.                 │
│                                                │
│  ScreenSense supports healthy screen habits.   │
│  It is not a medical device and does not       │
│  diagnose or treat any condition.              │
│                                                │
│                        [Next]                  │
└────────────────────────────────────────────────┘
```

`screensense/docs/wireframes-part-2.md` — onboarding step 2 of 3

```text
┌────────────────────────────────────────────────┐
│ Set your routine                    Step 2 of 3 │
│                                                │
│ Work interval       [ 20 ] minutes             │
│ Quick break         [ 20 ] seconds             │
│ Work hours          [ Start ] to [ End ]       │
│                                                │
│ You can change these choices in Settings.      │
│                                                │
│ [Back]                              [Next]     │
└────────────────────────────────────────────────┘
```

`screensense/docs/wireframes-part-2.md` — onboarding step 3 of 3

```text
┌────────────────────────────────────────────────┐
│ Optional blink monitoring           Step 3 of 3│
│                                                │
│ Get a blink rate estimate using your webcam.   │
│                                                │
│ [ ] I want to review blink-monitor consent     │
│                                                │
│ This is optional and starts off.               │
│                                                │
│ [Back]             [Skip]          [Finish]   │
└────────────────────────────────────────────────┘
```

**Components:** three-step progress label; welcome/privacy promise; break and work-hours preferences; optional blink-monitor introduction; Back, Next, Skip, and Finish navigation. The work interval and quick break defaults are 20 minutes and 20 seconds. Onboarding does not enable blink monitoring: the user must open and accept its separate consent panel.

**States and copy:**

- **Default:** step 1 introduces local privacy and includes the mandatory disclaimer; step 2 shows defaults; step 3 states the monitor is optional and off by default.
- **Hover/focus:** navigation controls have visible focus; step changes occur only on activation.
- **Empty:** no required personal details are collected. If optional work hours are blank, show `You can set work hours later in Settings.`
- **Error:** invalid preferences show `Check the values and try again.` Keep entered values and focus the first invalid field. If setup cannot save, show `Your setup couldn't be saved. Please try again.`

**Keyboard and accessibility:** Tab order follows the content and ends with navigation; Enter activates the focused action; Left/Right may move between steps only when focus is on the step navigation. Announce `Step n of 3` on navigation. Preserve values when moving Back. Clearly indicate optional fields, associate units with inputs, and support screen readers, keyboard-only operation, visible focus, high contrast, and 100–150% scaling.

## Blink-monitor consent

`screensense/docs/wireframes-part-2.md` — blink-monitor consent panel

```text
┌──────────────────────────────────────────────────────┐
│ Blink monitoring                            [Close]  │
│                                                      │
│ Blink rate estimate                                 │
│                                                      │
│ Blink monitoring uses your webcam on this device    │
│ only. No video or images are saved or sent anywhere.│
│                                                      │
│ The vision worker reports aggregated measurements.  │
│ Camera frames are discarded.                        │
│ You can turn it off at any time in Settings.        │
│                                                      │
│ [ ] I understand and want to enable blink           │
│     monitoring on this device.                      │
│                                                      │
│ [Not now]                    [Enable monitoring]    │
└──────────────────────────────────────────────────────┘
```

**Components:** clear feature title; exact privacy statement from the style guide; explanation that only aggregated measurements leave the vision worker; reminder that monitoring is optional and can be disabled; unchecked, explicit-consent checkbox; Not now and Enable monitoring actions. Enabling is impossible until the checkbox is selected. Show the camera tray indicator while monitoring is active.

**States and copy:**

- **Default:** checkbox is unchecked; `Enable monitoring` is disabled; the exact copy reads `Blink monitoring uses your webcam on this device only. No video or images are saved or sent anywhere.`
- **Hover/focus:** checkbox and buttons show visible focus; hover does not toggle consent.
- **Empty:** no camera device is required to read or dismiss consent. If no camera is available after opt-in, show `No camera is available. Blink monitoring remains off.`
- **Error:** if the monitor fails to start, show `Blink monitoring couldn't start. It remains off; you can try again in Settings.` Never imply it is active unless it has started.

**Keyboard and accessibility:** focus the consent checkbox on open; Space toggles it; Tab reaches Not now and Enable monitoring; Enter activates the focused button; Escape closes without enabling. Screen readers announce the full consent copy and whether Enable monitoring is unavailable. Do not rely on color for enabled state. Expose camera state in text and icon, and honor keyboard navigation, visible focus, high contrast, and scalable UI.
