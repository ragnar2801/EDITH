# Task tracker

> How work on Friday is tracked between sessions. One board per phase.
> Design and decisions: [`agents.md`](../../agents.md) · Phases: [`phases.md`](../phases.md)

## Boards

| Phase | Board | Status |
|-------|-------|--------|
| 1 — Tracker | [`phase-1.md`](phase-1.md) | Active |
| 2 — Research on demand | _created when Phase 1 is done_ | — |

## Task types

| Type | Meaning | How it closes |
|------|---------|---------------|
| **DECIDE** | An open choice (a library, a data source, a model, a rule) | Options compared (with a quick test where useful) → outcome written in the task → decision logged as `D-###` in `agents.md` |
| **BUILD** | Code or config to write | Works as described in "Done when", with tests where it's maths |
| **VERIFY** | Check that the phase does what it promised | Evidence written in the task |

## Fields

- **ID:** `T<phase>-<nn>`, e.g. `T1-12`. IDs are never reused or renumbered.
- **Status:** `todo` · `doing` · `blocked` · `done` · `dropped`
- **Owner:** `me` (the user), `Claude`, or `both`
- **Depends on:** tasks that must be `done` first. A BUILD task never starts before the DECIDE tasks it depends on are done.

## Rules

1. **Nothing below the 100-foot view is decided until its DECIDE task is done.** Library names and data sources in `agents.md` are proposals until then.
2. **Update the board table and the task's detail section together.**
3. **A DECIDE task isn't done until its outcome is in `agents.md`** as a new `D-###` row (and any affected doc is updated).
4. **New work discovered mid-task becomes a new task** at the end of the board, not scope creep in the current one.
5. **Commit messages start with the task ID**, e.g. `T1-12: pick NSE bhavcopy as primary India source`.

## Session routine

1. Read `CLAUDE.md`, then `agents.md` sections 2, 3 and 5, then the active board.
2. Pick the task to work on: the one marked `doing`, or the first `todo` whose dependencies are `done`, or the one I name.
3. Mark it `doing`. Work on it. Write the outcome or progress notes in its section.
4. Mark it `done` (or `blocked` with the reason). Commit and push.

## Moving to another tracker later

The IDs and sections map one-to-one onto GitHub Issues (title = `ID · name`, body = detail section, labels = type and status) if we ever want to move.
