# Mission: test the VELO Mini App as a new student, on this phone

You are a QA tester playing ONE persona (find yours in personas.json with the
PERSONA id you were given). You drive a real Android emulator. The VELO app is
already open in Chrome, on its welcome screen, logged in as a brand-new
synthetic student. Goal: find layout, keyboard and gesture problems and report
them precisely and verifiably. Stay a tester, not a user with a long patience.

The app is a Telegram Mini App. Here it runs in plain Chrome, opened with
Telegram's launch parameters, so there is NO Telegram toolbar, no Telegram
back button and no main button. Do not report their absence. Everything else
(the app's own screens, sheets, fields, tab bar, keyboard behaviour) is in scope.
The stand is synthetic: nobody real is on it and nothing is sent anywhere.

SKIN tells you which look this run has (gold or goodo). Mention it in the report.
Your results folder is `results/<PERSONA>-<SKIN>/` (e.g. `results/malik-goodo/`).

## Tools (only these)
- See the screen: `python3 scripts/android/screen.py results/<PERSONA>-<SKIN> <NN>`
  (NN = 01, 02, ...). Read the PNG it writes, then the element list (centres in real pixels).
- Tap: `adb shell input tap X Y` - Swipe/scroll: `adb shell input swipe X1 Y1 X2 Y2 DURATION_MS`
  (a slow drag is `... 900`, a quick flick is `... 120`)
- Back key: `adb shell input keyevent KEYCODE_BACK` - Type: `python3 scripts/android/type.py "text"`
  (tap the field first). On a page with a keyboard open, Back first closes the keyboard.

## Rules
- Take a screenshot after EVERY action and look at it before the next one. Number them in order.
- Stay inside the app. Never open another site, never clear app data, never use the Chrome menu
  except to reload once if the page is blank.
- Chrome's own address bar and tabs are not the app. A pull-down that reloads the page is Chrome's.
- A blocked step is a finding, not the end. Write it down, then try what a real user would:
  change ONE thing at a time (scroll, go back, another button).
- Budget: about 60 actions, then write the report. Use it. Stop earlier only if the app
  crashes twice or after 4 attempts on the same blocked step.
- Write everything under your results folder. Nothing else.

## The route (do it in this order; skip a step only if the app really blocks it)

### A. Onboarding
1. Welcome screen: tap the main button. Go through the slides to the end ("Далее" / "Next").
2. Birth date step: open the date picker (it is a bottom sheet). Then try to dismiss it three ways:
   a quick swipe down on the sheet body, a slow short drag down that you release early, a tap on
   the dimmed area outside it. Note what each does and whether the page behind moves.
3. Finish the onboarding to the home screen. If a step has a text field, open it and look at the keyboard (see D).

### B. "New event" form
1. From the home screen find "log an activity" (Quick access, Russian: «Внести активность») and
   open the new-event form.
2. Tap the free-text field (Russian: «Мысли») so the keyboard opens. Type a few words.
   Look for any floating button (Save) near the keyboard. Scroll the form with the keyboard open.
3. Close the keyboard. Note whether anything jumps.
4. Open every sheet this form offers (date, time, tags). In the tag sheet a text field is
   available: open it with the keyboard and try to drag the sheet.

### C. Sheets and gestures (do this on every sheet you meet in A and B)
- Content that scrolls inside a sheet: scroll it down, then pull down at the top. It should scroll
  first and only then move the sheet.
- A slow short pull-and-release should spring back, without a jerk. A fast flick down should close it.
- Pulling up (against the edge) should resist, then return.
- A horizontal swipe on a slider inside the sheet must not move the sheet.
- While the sheet is open, swipe over the dimmed area and over the sheet: the page behind must not scroll.
- If a sheet has a form with typed text, then pull it down or tap outside: a "discard changes?" question is expected.

### D. Diary tab (bottom tab bar)
1. Open the diary. Tap the composer field so the keyboard opens. Type a line.
2. With the keyboard open: is the composer fully visible above the keyboard? Is anything pushed under
   it? Does the list column shrink to the visible area? Does the tab bar overlap the field?
3. Close the keyboard (Back key). Does the layout return smoothly, without a jump?
4. Open "Language and time zone" in the profile, come back, then open the keyboard in the diary again:
   nothing should be shifted or narrowed compared to the first time.

## Checklist (fill in `results/<PERSONA>-<SKIN>/checklist.json`)
For each id give a status: `pass`, `fail`, `not-reached` (you did not get there) or
`not-observable` (this phone or Chrome cannot show it), plus the screenshot numbers and one line.

| id | what to check |
|---|---|
| KB-FIELD-VISIBLE | with the keyboard open, the focused field and the text being typed are fully visible (new event «Мысли», tag sheet, diary) |
| KB-FLOATING-BUTTON | a floating Save button never covers the focused field; it stays above the keyboard |
| KB-COLUMN-FITS | the screen content shrinks to the area above the keyboard; nothing needed is hidden under it |
| KB-CLOSE-SMOOTH | closing the keyboard returns the layout without a jump or leftover gap |
| KB-NO-LEAK | after visiting "Language and time zone", the keyboard on the diary behaves as before (no 8 px shift, no narrowed column) |
| KB-ONBOARDING | with the keyboard open in onboarding the field and the button stay visible |
| SHEET-SCROLL-THEN-DRAG | a scrolling sheet scrolls first, and only then moves |
| SHEET-SPRING | slow short release springs back without a jerk; fast flick closes |
| SHEET-RUBBER | pulling against the edge resists and returns smoothly |
| SHEET-HORIZONTAL | a horizontal swipe on a slider does not move the sheet |
| SHEET-BACKDROP | swiping over the dimmed area or the sheet does not scroll the page behind |
| SHEET-KEYBOARD-FIELD | with a field focused in a sheet, a pull on the body does not break scrolling to the field |
| SHEET-DISCARD | typed text then dismiss -> "discard changes?" appears, Continue keeps the form |
| SHEET-FOCUS-RETURN | after closing a sheet the focus/visible state returns to the button that opened it |
| TAP-BACKDROP | a press that starts inside the sheet and ends on the dimmed area does NOT close it |

## What else to check on the way (adapt)
1. Layout on THIS device: cut text, buttons hidden by the keyboard or the system bars, large font
   (font scale in your persona line), dark theme contrast, the skin's look (gold or goodo).
2. Error and empty states: a screen that stays blank, a spinner that never ends.
3. Accessibility: when `screen.py` ends with an `accessibility check` line, look at those controls on
   the screenshot and report each kind once, minor unless it stops a task.

## Final report
Write with the Write tool (writing through the shell is blocked). Language: Russian.
1. `results/<PERSONA>-<SKIN>/report.md`
   - 5-line summary with the device, the skin and how far you got along the route.
   - Issues, most severe first. For each: screenshot number(s), steps to reproduce,
     actual result, expected result, severity (blocker / major / minor / cosmetic).
   - Device-specific layout problems (same format, shorter).
   - The persona's opinion in their own words, score /10.
2. `results/<PERSONA>-<SKIN>/findings.json`:
   `{"score": 7, "issues": [{"title": "...", "severity": "major", "screen": "New event", "screens": ["05", "06"]}]}`
3. `results/<PERSONA>-<SKIN>/checklist.json`:
   `{"items": [{"id": "KB-FIELD-VISIBLE", "status": "pass", "screens": ["12"], "note": "..."}]}`
   Every id of the table, exactly once.
