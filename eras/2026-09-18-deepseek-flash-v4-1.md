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
- The seat: unchanged, and unchanged for a reason worth stating. It stays a
  steered generator not because V4.1 was judged and found wanting but because
  it has not been judged at all. `status = "experimental"` is probation: the
  route is live, the restriction holds, and a field arc on this build is what
  lifts it.

## Why the board row stays with the predecessor

The Datacurve board measured the 0731 build at 53% for $0.46 over 153 steps,
and the roster recorded that build's list price. V4.1 has no row here.

A successor carries its predecessor's weaknesses as a prior and none of its
numbers — the reading this roster applies to any successor before its own field
arc. A prior is not a finding. The fabrication measured on 0731 says what to
watch for on V4.1 and what a field arc must be built to detect; it does not say
what V4.1 does, and the roster must not be read as claiming it. The family's
releases have each been reported stronger than the last, which is equally
unmeasured here and equally unable to promote the build on its own.

So the row keeps the 0731 figures as predecessor evidence, marks every field
observation as the predecessor's, and marks the live build unmeasured.

## Verification

`agent-routing resolve generate --backend pi --allow-experimental` returns
`deepseek-flash` at max, and a live delegation through that route answered as
`deepseek-flash` with a clean exit.

## What lifts the probation

A field arc on V4.1 itself: a bounded implementation slice with named
acceptance probes, read afterwards for two things specifically — whether the
brief's explicit instructions were followed, and whether any identifier it
emitted was fabricated. Those are the two failures that closed the executor
question on the predecessor, so they are what a successor has to be measured
against. A fresh vendor benchmark is not that arc, and neither is a clean run
nobody adjudicated.
