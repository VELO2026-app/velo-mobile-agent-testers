# Acceptance: what the pilot has to prove

The pilot (FE-276) is accepted on the manual checklists the owner already had
to run by hand in the PRs of VELO2026-app/velo:

| PR | Topic | Source of the checklist |
|---|---|---|
| [#187](https://github.com/VELO2026-app/velo/pull/187) | FE-233 package 1: kit overlays (focus return, inert page, backdrop-press guard), iOS touch guard | "Пункт 4" and "Проверено" |
| [#194](https://github.com/VELO2026-app/velo/pull/194) | FE-233 package 2: sheet swipe from anywhere, spring, `dismissible` guard | "Чек-лист на устройстве" |
| [#205](https://github.com/VELO2026-app/velo/pull/205) | FE-261 №6: the focused field stays above the floating Save pill | "Что смотреть на iPhone" |
| [#206](https://github.com/VELO2026-app/velo/pull/206) | FE-261: `:global(html.is-keyboard-open)` rules in scoped styles | "Чек-лист для проверки" |

Two separate questions, two separate gates.

## Gate 1: coverage

The agent's `checklist.json` has every id below exactly once, and each is
`pass`, `fail`, `not-reached` or `not-observable` with a screenshot number.
The run is accepted on coverage when at least **10 of the 15 ids** are
`pass` or `fail` (i.e. actually observed), and every `not-observable` has a
reason that matches the "Not observable here" column.

| id (briefs/velo-student.md) | PR item | Observable on Android emulator + Chrome? |
|---|---|---|
| KB-FIELD-VISIBLE | #205 "поле и набираемый текст выше кнопки"; #187 п.3 keyboard + field in a sheet; #206 diary composer above the keyboard | yes, the real soft keyboard |
| KB-FLOATING-BUTTON | #205 "кнопка над клавиатурой" | yes |
| KB-COLUMN-FITS | #206 "колонка сжимается до `--velo-vvh`" (diary, chat, timezone list) | yes (chat needs the comms stub: reachable only if the seed has a chat; otherwise `not-reached`) |
| KB-CLOSE-SMOOTH | #205 "закрыть клавиатуру: кнопка на месте"; #206 "плавно, около 250 мс, без прыжка" | partly: a jump is visible, 250 ms smoothness is not (screenshots are not frames) |
| KB-NO-LEAK | #206 "открыть «Язык и часовой пояс», вернуться, затем клавиатура: нет сдвига 8 px" | partly: 8 px is below what an agent reliably sees; the smoke check measures it exactly (`kbClass`, `vvh`) |
| KB-ONBOARDING | #206 "Онбординг: отступы плотнее, поле и кнопка видны" | yes |
| SHEET-SCROLL-THEN-DRAG | #194 "прокрутить список вниз, затем потянуть вниз" | yes (real touch through `adb input swipe`) |
| SHEET-SPRING | #194 "недалеко и медленно: пружина; быстрый бросок: закрывается" | partly: the spring itself is motion; an agent sees the end state only |
| SHEET-RUBBER | #194 "потянуть вверх: резина, возврат плавный" | partly, same reason |
| SHEET-HORIZONTAL | #194 "горизонтальный свайп и ползунок настроения не двигают шит" | yes if a sheet with a slider is reachable; else `not-reached` |
| SHEET-BACKDROP | #187 п.4 "свайп по подложке и по шиту: фон не двигается" | yes |
| SHEET-KEYBOARD-FIELD | #194 "клавиатура: поле в шите, жест по телу не ломает прокрутку к полю"; #187 п.3 | yes |
| SHEET-DISCARD | #194 "ввести комментарий, затем свайп / подложка / Отмена: «Сбросить изменения?»" | only on a sheet with a form; the report-user sheet is behind a block flow, so usually `not-reached` |
| SHEET-FOCUS-RETURN | #187 "фокус после закрытия" | no visible cue on a touch phone: expected `not-observable` |
| TAP-BACKDROP | #187 "тап по подложке после выделения текста"; #194 "нажатие внутри окна не закрывает" | partly: a press that starts inside and ends outside needs a drag, `adb input swipe` can do it |

### Not observable here (known up front, by design of the lane)

Taken from the checklists, these need Telegram itself and stay with the owner's
manual check or the Telegram lane ([telegram-lane.md](telegram-lane.md)):

- Telegram's vertical swipe not collapsing the Mini App over a sheet (`disableVerticalSwipes`) - #194.
- Telegram Desktop mouse drag on the handle - #194.
- Reduced motion without spring - #194 (an Android setting could drive it; not in the pilot).
- iPhone-only items: the iOS touch guard comparison (#187 п.4), the "scroll finishes mid-gesture" case (#194), the iPhone Telegram safe-top of 70 px (#206).
- The top inset and the floating Telegram chrome: absent in a plain Chrome page by construction.

## Gate 2: detection power (the real test)

Coverage says the agent looked. This gate says it can **see a bug that the
owner found by hand**. Run the same scenario on the commit **before** each fix,
then on the fix:

| What | `velo_ref` before the fix | `velo_ref` after the fix |
|---|---|---|
| #206 keyboard rules in scoped styles | `fd17e61e44be0160bfe6c7f1560d82445b68626d` (first parent of the merge `822d43e8`) | `822d43e8f4e14f17134d4545120648a2abaaaa75` |
| #205 focused field under the floating Save | `a0f56f878999df741bfacfe0741f35b6cd97a62f` (first parent of the merge `fd17e61e`) | `fd17e61e44be0160bfe6c7f1560d82445b68626d` |

Pass: on the "before" commit the report names the symptom (the field hidden by
the Save pill for #205; for #206 the shifted or narrowed column) and on the
"after" commit it does not. Fail: the agent reports nothing on the buggy commit
(then the agent is too weak for this class of bugs: try `model=opus`) or it
reports the same symptom on both (a false positive).

Honest limit, from the PR text itself: the #206 bug shows as an **8 px** shift.
A screenshot agent will probably not see 8 px, so for #206 the deterministic
evidence is the smoke check (`scripts/velo/smoke.py`: `kbClass`, `vvh` before and
after), and the agent is only expected to catch the visible consequence (the
narrowed column on the timezone list, the stray flex on `<html>`). #205 is a
large visible bug and is the real detection test.

How to run the pair (needs the Claude key, see README):

```bash
gh workflow run velo-android.yml -R VELO2026-app/velo-mobile-agent-testers \
  -f velo_ref=a0f56f878999df741bfacfe0741f35b6cd97a62f -f skins=goodo -f personas=malik
gh workflow run velo-android.yml -R VELO2026-app/velo-mobile-agent-testers \
  -f velo_ref=fd17e61e44be0160bfe6c7f1560d82445b68626d -f skins=goodo -f personas=malik
```

## Decision after the first runs

Keep the lane when gate 1 passes and gate 2 catches #205. Otherwise: do not
widen it; use Playwright Android (deterministic, same checks by script) or stay
with manual checks, and say so in FE-276.
