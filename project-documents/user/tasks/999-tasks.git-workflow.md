---
docType: tasks
layer: project
audience: [human, ai]
description: Helpful git workflow reminders (pre-commit integration)
dateCreated: 20260308
dateUpdated: 20260308
---

# Git Workflow Notes

These are reminders for the developer to keep commits clean and avoid
hook failures.

1. Stage your changes as usual:

```sh
git add .
```

2. Run pre-commit on the staged files before committing.  This runs the
same hooks that will execute during `git commit`, but lets you fix the
issues _before_ attempting the commit:

```sh
pre-commit run --files $(git diff --name-only --cached)
```

3. If the previous step modified any files, re-stage them and inspect the
changes.  Once everything is formatted/linted, commit normally:

```sh
git commit
```

At this point the pre-commit hook will still run, but there will be nothing
to fix and the commit will succeed on the first try.  Consider creating a
shell alias or git command to wrap steps 1–3 if you find yourself doing
this frequently.

These notes are intentionally simple and live in the tasks directory so
they're easy to search for when you forget the exact sequence.
