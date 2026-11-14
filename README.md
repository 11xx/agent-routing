# agent-routing

Which model runs a task, at which effort, and which subscription pays for it.

If you run more than one coding agent, the choice of model for each kind of
work ends up copied into instruction files, agent definitions and scripts.
A new model ships, some of the copies are missed, and an agent starts work
on a tier you meant to stop using.

`agent-routing` keeps that choice as data in one Git repository. A caller
names the kind of work (a profile such as `implement` or `review`) and the
CLI it runs on (Claude Code, Codex, Pi or OpenCode), and gets back the
model, effort and provider that hold that seat. Changing a seat is one
command that validates the data and commits it, and the next lookup returns
the new answer.

It does not read the task to choose a profile, and it starts no agent: the
caller picks the profile and runs the route. The data in this repository is
its author's own roster and field notes, so read it as a worked example and
edit it into yours.

## Install

```sh
git clone https://github.com/11xx/agent-routing
ln -s "$PWD/agent-routing/bin/agent-routing" ~/.local/bin/agent-routing
```

Unix only, with Python 3.12 or later and Git; it uses the standard library
alone. The command reads the data from the checkout the link points at, and
every edit is a commit there.

## Ask for a route

```sh
agent-routing resolve implement --backend codex --json   # the seat's model, effort and provider
agent-routing check MODEL EFFORT                         # exits 1 on a prohibited tier
agent-routing card MODEL                                 # a model's seats, guards and field notes
```

`resolve` prints one JSON object. An instruction file or a launcher that
carries these commands names no model, so a roster change needs no edit
there.

## Change the roster

```sh
agent-routing set-seat implement --backend codex --model MODEL --effort high \
  --when "Bounded implementation from a written brief." \
  --why "Level with the tier above on review findings at half the price." \
  --dry-run                                  # preview; drop --dry-run to commit

agent-routing note --model MODEL --kind weakness --area review \
  --claim "Missed a race its own tests did not exercise." \
  --cause executor --evidence "review of the queue change"

agent-routing undo --why "Seated the wrong tier."   # reverses the latest edit in a new commit
agent-routing page                                  # the same edits from a local web page
```

An edit validates all three data files and makes one Git commit of the data.
It deploys and pushes nothing. Field notes are dated evidence for whoever
chooses a seat; no routing answer reads them.

## Where the rest is

`agent-routing` with no arguments prints the guide, which is the contract for
every command, and each command has `--help`. [DELEGATION.md](DELEGATION.md)
covers how work reaches an executor: roles, briefs and what each CLI needs at
launch. `bin/check-change` is the gate a change to the code passes, and its
header says what it checks.

[agent-delegate](https://github.com/11xx/agent-delegate) launches runs on
these routes, [arc](https://github.com/11xx/arc) reads the review ladder, and
[tapes](https://github.com/11xx/tapes) takes the list prices.

## License

Public domain, under the [Unlicense](UNLICENSE).
