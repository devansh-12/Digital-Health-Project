# Wireframes part 1

Assumption: these are compact desktop windows and menus using the Style Guide tokens; controls remain usable at 150% scaling.

## Tray menu

`screensense/docs/wireframes-part-1.md` — tray menu layout

```text
┌─────────────────────────────┐
│ ScreenSense                 │
│ Reminders: Active           │
├─────────────────────────────┤
│ Open dashboard              │
│ Start Eye Yoga (60s)         │
│ Take a quick break (20s)     │
│ Pause reminders              │
├─────────────────────────────┤
│ Settings                    │
│ Quit                        │
└─────────────────────────────┘
```

**Components:** tray icon; app name; text status; dashboard, Eye Yoga, quick-break, pause/resume, settings, and quit menu actions. Use the green icon when active, grey when paused or suppressed, and an amber dot when a reminder is due. Show the camera dot only while optional monitoring is running.

**States and copy:**

- **Default:** `Reminders: Active`; menu actions as shown.
- **Hover/focus:** highlight the focused row and show a visible focus ring; do not change its label or trigger it.
- **Empty:** if there is no current status to show, display `Status unavailable` and keep menu actions available.
- **Error:** if tray integration fails, show a non-blocking app notification: `ScreenSense couldn't show its tray menu. Reopen the app to try again.` Keep the app open so the user can retry or quit.

**Keyboard and accessibility:** open through the operating system's tray keyboard command; Up/Down move through items, Enter activates, and Escape closes the menu. Provide accessible names for the icon and each action. Status and icon color must both convey state. Preserve system high-contrast mode and visible keyboard focus.

## Break overlay

`screensense/docs/wireframes-part-1.md` — break overlay layout

```text
       (dimmed desktop; not click-through blocking)

       ┌─────────────────────────────────────┐
       │             (20 s ring)              │
       │        Time to rest your eyes 👀     │
       │                                     │
       │  A short pause may help you reset.  │
       │                                     │
       │ [ Eye Yoga (60s) ]  [Quick break]   │
       │ [ Snooze 5 min ]    [ Skip ]        │
       └─────────────────────────────────────┘
```

**Components:** centered card on a softly dimmed desktop; 20-second ring with numeric countdown; one short prompt; four actions. Eye Yoga is the primary action. The overlay is dismissible and never locks the screen. For a queued reminder after a call, replace the prompt with `Meeting's over. Want a quick eye break?`

**States and copy:**

- **Default:** `Time to rest your eyes 👀`; ring begins at 20 seconds; show all four actions.
- **Hover/focus:** emphasize the hovered or focused button without moving the layout; keep the primary action visually distinct.
- **Empty:** if no break type is available, show `Ready to rest your eyes?` and offer `Close` only.
- **Error:** if the selected activity cannot start, keep the overlay open and show `That break couldn't start. Please try again.` Keep all actions available.

**Keyboard and accessibility:** initial focus goes to the primary action without activating it. Tab and Shift+Tab visit all actions; Enter or Space activates; Escape dismisses the overlay. Announce the prompt and action labels to screen readers. Expose the countdown as a timer and announce meaningful milestones, not every second. Keep body text at least 4.5:1 contrast, pair ring color with its numeric value, and support reduced motion and 100–150% scaling.

## Eye Yoga player

`screensense/docs/wireframes-part-1.md` — Eye Yoga player layout

```text
┌──────────────────────────────────────────────────────────────┐
│ Eye Yoga (60s)                                      [ Exit ]  │
│                                                              │
│                    [step illustration]                       │
│                                                              │
│                         Palming                              │
│       Rub palms, cup them over closed eyes. Breathe slowly.   │
│                                                              │
│   Step 1 of 6     (progress ring: 10 s remaining)             │
│                                                              │
│                         [ Pause ]                            │
└──────────────────────────────────────────────────────────────┘
```

**Components:** large step illustration/animation; step name; one-line instruction; step count; progress ring and remaining time; Pause/Resume and Exit controls. The six 10-second steps are Palming, Fast blinking, Figure eight, Near-far focus, Up-down-left-right, and Slow eye rolls. Reduced motion uses a static illustration with the same text instructions.

**States and copy:**

- **Default:** show the current step and instruction; control label is `Pause`.
- **Hover/focus:** highlight the control and show a visible focus ring; do not start or exit on hover.
- **Empty:** if no routine steps are available, show `This routine isn't available right now.` with `Quick break` and `Exit` actions.
- **Error:** if the step timer or illustration fails, retain the instruction as text and show `The animation paused. You can continue with the written steps.` Offer `Continue` and `Exit`.
- **Paused:** stop the timer; replace `Pause` with `Resume`; keep `Exit` available.
- **Completed:** show `Nice. Your eyes thank you.` and a `Done` action.

**Keyboard and accessibility:** focus the current step heading when the player opens; Tab and Shift+Tab reach Pause/Resume and Exit; Space toggles Pause/Resume; Escape exits. Announce each step name and instruction when it changes, and expose progress as step count plus time remaining. Every movement has written instructions. Keep motion at or below 0.5 Hz, honor reduced-motion settings, use visible focus, maintain WCAG AA contrast, and support 100–150% scaling.
