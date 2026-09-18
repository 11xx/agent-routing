# Model era: DeepSeek Flash moves to V4.1 under its unversioned id (2026-09-18 → )

DeepSeek's live model list carries the Flash line only as `deepseek-flash`,
named V4.1 Flash, and the versioned id the roster pinned is deprecated. The
provider keeps the unversioned id across point releases, so it is the one that
survives the next one; the roster and the `generate` route follow it.

## What moved and what did not

- The build: V4 Flash 0731 → V4.1 Flash. The live list, last modified
  2026-09-17, prices it at 0.30 cache-miss input, 1.20 output, and 0.006 cached
  per million — roughly twice the 0731 input and four times its output.
- The id: `deepseek-v4-flash` → `deepseek-flash`. The versioned id still
  answers, which is why the old route kept working; nobody promised it would.
  What it answers *as* is unconfirmed — the resellers carry V4 Flash and V4.1
  Flash as separate models, and pi still prices the versioned id at the 0731
  rates, so it may be serving the predecessor rather than aliasing the new
  build. Route on the id the provider publishes, not on the one that still
  replies.
- The seat: unchanged. Still a steered generator, never an implementer of
  record, reviewer, planner, or the last model to touch shipped work.

## Why the board row stays with the predecessor

The Datacurve board measured the 0731 build at 53% for $0.46 over 153 steps,
and the roster recorded that build's list price. V4.1 has no row here. The
fabrication record is the family's and is inherited; the capability numbers are
a build's and are not. The row keeps the 0731 figures as predecessor evidence
and marks the live build unmeasured, the reading this roster applies to any
successor before its own field arc.

## Verification

`agent-routing resolve generate --backend pi --allow-experimental` returns
`deepseek-flash` at max, and a live delegation through that route answered as
`deepseek-flash` with a clean exit.
