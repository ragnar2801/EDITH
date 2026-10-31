# Task tracker

> How work on Friday is tracked between sessions. One board per phase.
> Design and decisions: [`agents.md`](../../agents.md)

## Boards

| Phase | Board | Status |
|-------|-------|--------|
| 1 — Tracker | removed 2026-10-31 (in git history) | Closed |

## Task shape

Tasks are **engineering tasks sized as a feature or an infrastructure slice**, about 10 per phase. Each one is something I can test end to end when it's done. Prefer feature tasks.

| Kind | Meaning |
|------|---------|
| **Feature** | A user-visible capability, built across backend, database and UI (e.g. "Holdings: record what I own") |
| **Infra** | Plumbing that features run on (e.g. project skeleton, scheduling) |
| **Verify** | Proving a phase works on real data |

Every task has:
- **Goal:** what I'll be able to do when it's done, in one or two lines
- **Scope:** what gets built
- **Decisions:** choices to make *before* building, with candidates. Each is logged as a `D-###` in `agents.md` when made
- **Done when:** testable acceptance checks

## Fields

- **ID:** `T<phase>-<nn>`, e.g. `T1-05`. From board version 2 on, IDs are never reused or renumbered.
- **Status:** `todo` · `doing` · `blocked` · `done` · `dropped`
- **Owner:** `me` (the user), `Claude`, or `both`
- **Depends on:** tasks that must be `done` first

## Rules

1. **Decide first, then build.** A task starts with its *Decisions* list. Library names and data sources in `agents.md` are proposals until a task decides them.
2. **Every decision is logged** as a new `D-###` row in `agents.md`, and written under the task as "Decided: … (D-###)".
3. **Update the board table and the task's section together.**
4. **New work discovered mid-task becomes a new task** at the end of the board, not scope creep in the current one.
5. **Commit messages start with the task ID**, e.g. `T1-05: India prices fetcher with NSE primary, Yahoo fallback`.

## Session routine

1. Read `CLAUDE.md`, then `agents.md` section 2, then the active board.
2. Pick the task to work on: the one marked `doing`, or the first `todo` whose dependencies are `done`, or the one I name.
3. Mark it `doing`. Work through its *Decisions* with me, then build. Write progress notes in its section.
4. Mark it `done` when every *Done when* check passes (or `blocked` with the reason). Commit and push.

## Moving to another tracker later

Each task maps one-to-one onto a GitHub Issue (title = `ID · name`, body = its section, labels = kind and status).
