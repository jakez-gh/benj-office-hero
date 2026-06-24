# Multi-Agent Coordination — Office Hero

Each agent the user deploys reads this file first, then claims a workstream by
writing a `agents/<agent-id>.md` heartbeat file and registering in `ROSTER.md`.

---

## How this works

1. **Read** this README and `ROSTER.md`
2. **Pick** an unclaimed workstream from `WORKSTREAMS.md`
3. **Claim** it: write `.agents/agents/<your-id>.md` and add a line to `ROSTER.md`
4. **Work** the tasks; update your heartbeat file after each commit
5. **Wait** using a randomized prime-number pause (seconds) between polling cycles
   so agents don't all wake simultaneously — pick any prime between 7 and 97
6. **Handoff**: if you go offline mid-task, set your status to `paused`; another
   agent may pick it up after seeing no heartbeat update for 3+ cycles

## Heartbeat file format

`.agents/agents/<agent-id>.md`:

```markdown
---
agent: <id>          # short unique label e.g. "alpha", "beta", or a hash prefix
status: active       # active | paused | done | dead
workstream: <id>     # from WORKSTREAMS.md
last_commit: <sha>
last_updated: <ISO timestamp>
---

## Current task
<one-line description of what is being worked on right now>

## Completed this session
- <sha> <description>

## Blocked on
<anything blocking — or "nothing">
```

## Coordination rules

- **No two agents claim the same workstream.** Check `ROSTER.md` before claiming.
- **File conflicts**: agents work in separate areas when possible. If two agents must
  touch the same file, the second one rebases on the first's commit before pushing.
- **Communication**: drop notes in `.agents/inbox/<agent-id>.md` for another agent.
  Each agent checks its inbox at the start of every cycle.
- **cf CLI**: use `cf status` / `cf next` / `cf set slice N` / `cf build` for all
  slice tracking. The open-work index (`951-tasks.open-work.md`) is the shared task queue.
- **Commits**: follow the project's commit-early-and-often rule. Push after each commit.
- **Reviews**: run `sq review code --diff origin/main` before considering a slice done.

## Prime-pause table (pick one each cycle)

7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97

Use `import random; random.choice([7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97])`
or just pick one. Vary it cycle-to-cycle to spread load.
