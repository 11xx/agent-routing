# agent-routing

Which model runs a task, at which effort, and which subscription pays for it.

If you run more than one coding agent, the choice of model for each kind of
work ends up copied into instruction files, agent definitions and scripts.
A new model ships, some of the copies are missed, and an agent starts work
on a tier you meant to stop using.

`agent-routing` keeps that choice as data in one Git repository. A caller
names the kind of work (a profile such as `implement` or `review`) and the
CLI it runs on (Claude Code, Codex, Pi or OpenCode), and gets back the
model, effort and provider assigned to that work there, which is called a
seat. Changing a seat is one command that validates the data and commits
it, and the next lookup returns the new answer.

It does not read the task to choose a profile, and it starts no agent: the
caller picks the profile and runs the route. The data in this repository is
its author's own roster and field notes, so read it as a worked example and
edit it into yours.

## Install

```sh
git clone https://github.com/11xx/agent-routing
mkdir -p ~/.local/bin
ln -s "$PWD/agent-routing/bin/agent-routing" ~/.local/bin/agent-routing
```

Unix only. It needs Bash, a `readlink` that takes `-f`, Git, and Python 3.12
or later as `python3`; the Python code uses the standard library alone. The
command reads the data from the checkout the link points at, and every edit
is a commit there.

## Ask for a route

```sh
agent-routing resolve implement --backend codex --json   # the seat's model, effort and provider
agent-routing check MODEL EFFORT                         # exits 1 on a prohibited tier
agent-routing card MODEL                                 # a model's seats, guards and field notes
```

`resolve` prints one JSON object. A caller that resolves a profile when it
launches gets the current seat without keeping its own copy of the roster.

## Change the roster

```sh
agent-routing set-seat implement --backend codex --model MODEL --effort high \
  --when "Bounded implementation from a written brief." \
  --why "High effort is enough for bounded implementation." \
  --dry-run                                  # preview; drop --dry-run to commit

agent-routing note --model MODEL --kind weakness --area review \
  --claim "Missed a race its own tests did not exercise." \
  --cause executor --evidence "review of the queue change"

agent-routing undo --why "Seated the wrong tier."   # reverses the latest edit in a new commit
agent-routing page                                  # the same edits from a local web page
```

An edit validates all three data files and makes one Git commit of the data.
It deploys and pushes nothing. If the preview asks for `--pool-rank N`,
rerun it with a place in the subscription's order; the refusal lists the
order and suggests one. Field notes are dated evidence for whoever chooses a
seat; no routing answer reads them.

## Where the rest is

`agent-routing` with no arguments prints a one-screen map of what it does.
`agent-routing guide <topic>` holds each command's contract, one subject at a
time, and `agent-routing --help` lists the commands.
[DELEGATION.md](DELEGATION.md) covers how work reaches an executor: roles,
briefs and what each CLI needs at launch. `bin/check-change` is the gate a
change to the code passes, and its header says what it checks.

[agent-delegate](https://github.com/11xx/agent-delegate) launches runs on
these routes, [arc](https://github.com/11xx/arc) reads the review ladder, and
[tapes](https://github.com/11xx/tapes) takes the list prices.

## License

Public domain, under the [Unlicense](UNLICENSE).
