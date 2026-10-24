# Model era: Opus 5.5 stable from low to xhigh, head at high, implementer at low (2026-10-24 → )

Opus 5.5 held one stable tier, xhigh, for the head, Claude implementation,
first-party review and design. High was explicit-only, medium available but
unseated, low an experimental implementation capacity trial, and max
explicit-only. On 2026-10-24 the operator made every tier from low to xhigh
stable, banned max, and split the defaults by seat.

## The operator's direction

> add low medium and high to stable in routing alongside xhigh. it's all useful
> in all efforts depending on task. and the default should now be high for
> lead, opus low for implementer on claude family (if sonnet is a default seat
> anywhere replace it). medium and xhigh are stable but low and high already
> cover pretty much everything. xhigh is still useful in deep reviews and
> resonings. max is banned.

It is operator field judgment. No row of this matrix measures any Opus 5.5
tier, and nothing here calibrates the effort curve.

## Seats

| Seat (claude backend) | Before | After |
| :--- | :--- | :--- |
| head default (`plan`) | no binding | Opus 5.5 high (`plan:opus`) |
| `plan --variant opus-xhigh` | — | Opus 5.5 xhigh |
| `implement` default | Opus 5.5 xhigh (`implement:opus`) | Opus 5.5 low (`implement:opus-low`) |
| `implement` named tiers | `opus-low`, experimental | `opus-medium`, `opus-high`, `opus-xhigh`, stable |
| `execute` default | Opus 5.5 xhigh | Opus 5.5 high |
| `review` default | Opus 5.5 xhigh | Opus 5.5 xhigh |
| `design` | Opus 5.5 xhigh | Opus 5.5 high; `--variant xhigh` for deep design review |
| `explore --variant opus` | Opus 5.5 xhigh | Opus 5.5 high |
| `computer-use --variant opus` | Opus 5.5 medium, experimental | unchanged |
| relay proxy shells (`codex`, `pi`, `opencode`) | sonnet low | opus low |

The head runs high and Claude implementation low, as directed. Review keeps
xhigh because the direction names deep reviews as what xhigh is for.
`execute` follows the head rather than the implementer: it is the shape for
broad work where technical judgment remains material, and its Codex default
is Sol xhigh, so a low fallback from it would cut the judgment the shape
exists for. `design` follows the head too, because taste is the head model's
axis, with xhigh kept as a named deep-review variant.

Sonnet held one default seat: the relay proxy shells, through the
version-agnostic `sonnet` alias. They move to `opus` at low. Sonnet 5.5's
operator-directed trial selection stays as it was; it was never a default.
Haiku 5.5 high keeps the `explore` and `extract` seats.

`plan` gains a claude binding. Planning was already the head model's own seat
in prose, but no route answered `plan` on the claude backend, so `seats`
reported the head default as absent. The binding makes the head default a
resolvable fact at high.

## Review tiers

| Effort | Before | After |
| :--- | :--- | :--- |
| low | author floor 1 | review tier 1 |
| medium | author floor 1 | review tier 1 |
| high | author floor 2 | review tier 2 |
| xhigh | review tier 2 | review tier 2 |
| max | author floor 4 | author floor 4, prohibited |

Every number is the one the tier already carried, so no author's review
requirement moves. The ladder matches Fable 5.1, Sonnet 5.5 and GPT-6.1 Sol at
each effort, and it never falls as effort rises. Xhigh stays at 2 rather than
Astra xhigh's high-stakes 3: being the deep-review tier buys depth inside the
tier-2 seat, not a higher author floor, and nothing here measures it above
Sol xhigh. Seating it at 3 would also leave an Opus-authored xhigh diff with
no stable cross-family reviewer short of Astra xhigh. Max keeps floor 4 so a
diff authored there still needs the top review tier.

Ranks in the Anthropic pool are Haiku high 1, then Opus low 2, medium 3, high
4 and xhigh 5.

## Native definitions

`agent-delegate` ships one pinned implementer per stable tier:
`implement-opus-low` (the default), `implement-opus-medium`,
`implement-opus-high` and `implement-opus-xhigh`. The single `implement-opus`
definition at xhigh and the experimental `implement-opus-low` trial collapse
into that set, so each route has exactly one definition. No definition runs
at max.
