# Erik Corkran's AI‑Project Process (human steps)

This document is a distilled, human‑readable version of the
**AI Project Guide** methodology maintained by Erik Corkran
(see <https://github.com/ecorkran/ai-project-guide>).  It outlines the
seven phases and supporting structure that his workflow uses when
building software with AI assistance.

> The goal is to give you a separate set of "human steps" that follow
> Erik's process.  You can keep using the existing solo process above,
> or switch to this one as desired.

---

## Overview

Erik's approach divides a project into **phases** that gradually refine
an idea into runnable code.  AI tools (Claude, Cursor, Windsurf, etc.)
are treated as collaborators that consume structured context from your
repo.  A companion tool called *Context Forge* automates prompt
assembly, but the human steps are essentially the same with or without
it.

The phases are:

1. **Concept** – capture the idea
2. **Specification** – nail down requirements and architecture
3. **Slice planning** – break work into vertical slices
4. **Slice design** – design each slice in detail
5. **Task breakdown** – let AI turn designs into tasks
6. **Task enhancement** – polish tasks for clarity
7. **Implementation** – AI writes code, runs tests, iterates

There are also supporting directories for guides, frameworks, tools,
and domain knowledge; you keep your own project work separate in a
`user/` folder.

---

## Human steps by phase

### Phase 1 – Concept

1. In `project-documents/user/project-guides/` create
   `001-concept.<your-project>.md`.
2. Write a plain-English description of what you're building, target
   users, and success metrics.
3. (Optional) invoke the AI with a prompt like:
   "Expand this concept into a list of functional requirements,
   non‑functional qualities, and potential risks."
4. Save or commit the file so the AI can reference it later.

### Phase 2 – Specification

1. Add `002-spec.<project>.md` alongside the concept doc.
2. Flesh out the tech stack, high‑level architecture, APIs, and data
   model.
3. Ask the AI to generate a short ADR (architecture decision record)
   summarizing major choices.
4. Capture any constraints or dependencies.

### Phase 3 – Slice planning

1. Split the work into *slices* – vertical pieces that deliver value on
   their own (e.g. "user auth", "report export").
2. Create a simple list in a new file or spreadsheet; identify
   priorities and rough effort.
3. Record this plan in the `user/` area so later phases can reference
   it.

### Phase 4 – Slice design

1. For each slice, create `user/slices/nnn-slice.<name>.md` (nnn is a
   zero‑padded index).
2. Describe the slice’s goal, inputs/outputs, interfaces, and
   dependencies. Sketch diagrams if helpful.
3. Define success criteria and any edge cases.
4. Optionally have the AI suggest patterns or pull from framework
   guides.

### Phase 5 – Task breakdown

1. Feed a slice design to the AI with a prompt like
   "Break this slice into implementable tasks."
2. The AI produces a file `user/tasks/nnn-tasks.<name>.md` listing
   discrete steps (e.g. "add `/login` route", "write unit tests for
   auth service").
3. Review and adjust tasks for your own understanding.

### Phase 6 – Task enhancement

1. Let the AI elaborate each task with file paths, test hints, edge
   cases, and clarifications.
2. This step is often optional by 2026; skip if tasks are already clear.
3. Save the polished tasks back to the `tasks` file.

### Phase 7 – Implementation

1. Open a coding session with your AI assistant, giving it the
   relevant slice/task context (Context Forge automates this).
2. Ask the AI to work through a task: generate code, add tests,
   commit as it completes each bullet.
3. Review the output, run the tests locally, and push changes.
4. Mark tasks done and iterate if needed.

Repeat phases 4–7 for each slice until the project is ready to
deploy.

---

## Additional human guidance

* **Directory structure** – your project root will contain
  `project-documents/ai-project-guide/` (the submodule) and
  `project-documents/user/` (your files).  Do not edit the former
  directly.
* **Using tools** – running `scripts/setup-ide` generates rules for your
  AI coding environment (Claude, Cursor, etc.).
* **Context Forge** – install with `npx @context-forge/mcp` to build
  context prompts automatically.
* **Iteration** – you don’t have to follow every phase sequentially;
  the guide encourages cycling through slices as requirements evolve.
* **Customization** – the repository includes framework/tool/domain
  guides you can adapt for your stack.

---

This document gives a human‑friendly checklist to pair with the
existing step‑by‑step approach.  You can either maintain it manually or
use the ai-project-guide materials directly in your own projects.

*See also the original guide at
<https://github.com/ecorkran/ai-project-guide> for the full, living
methodology.*
