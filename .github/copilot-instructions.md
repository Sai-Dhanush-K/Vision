# GitHub Copilot Instructions

Before doing project work, read `context.md`, `instructions.md`, and `progress.md` from the repository root. Treat `instructions.md` as mandatory workflow policy and `progress.md` as the current state log.

Work on one small, testable increment at a time. Never generate the whole application or implement multiple phases in one go. Follow the full inspect → scope → implement → test → correct if needed → review → update `progress.md` → commit if verified → stop workflow defined in `instructions.md`.

The starting task is Phase 1 only: inspect the existing repository and locate the prerecorded walking POV video; check the current environment, inspect video metadata, and verify frame reading with OpenCV. Do not begin YOLO, Gemini, speech, voice commands, currency recognition, tracking, or live-camera support yet.

After each project-related chat exchange, update `progress.md` with changes or decisions, actual tests and results, blockers, and the next single permitted step. Do not claim commands or tests were run unless they were. Do not push to a remote unless the user explicitly asks. If a required verification depends on the user, provide precise instructions and pause.
