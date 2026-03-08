---
docType: reference
layer: project
audience: [human, ai]
description: Directory inventory for user/ui/ assets and mockups
dateCreated: 20260308
dateUpdated: 20260308
---

# user/ui/ — Directory Inventory

Contains user interface artifacts: mockups, screenshots, design notes, and
reusable UI components or assets that are not code. This directory helps keep
visual design assets versioned alongside the project.

## What goes here

- PNG/SVG mockups or flow diagrams
- React component screenshots for documentation
- Storybook stories or snapshot images
- Any large binary assets needed for UI design

## What does NOT go here

- React source code (goes in `apps/` or `packages/`)
- CSS or style files (stay with the codebase)
- Documentation that belongs in `docs/` or `project-documents/`

Keep assets small; avoid committing vendor UI libraries here. If designers need
a place to store drafts, this directory is acceptable but review periodically.
