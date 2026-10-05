# Cycle 03 — GitHub connection and verification loop

Date: 2026-10-06, Asia/Seoul. Target: Dowon-Kang/Flowlens only.
Baseline: reviewed v0.2.0 ZIP already uploaded by the user; preserve original archive.

## Acceptance criteria before implementation
1. Restore ordinary versioned source from the uploaded ZIP, with checksum/path verification.
2. Reproduce then fix typed Dio requests, multiline imports and priority selection.
3. Bound ZIP decompression before reading and account for all files in coverage.
4. Keep System Flow at eight nodes including the virtual entry point.
5. Run unit, Skill, JS, actual HTTP ZIP and browser tests; record all failures.
6. Run real GitHub/same-commit ZIP in CI, inspect logs and fix failures without force-push.
7. No execution of target VibeCare code, paid AI calls, deployment or unrelated repo changes.

Loop: failing test → minimal fix → local checks → source commit → CI logs → correction → Markdown record.
Network-blocked, partial and untested results must stay explicit. A Skill is a development procedure, not an autonomous worker.
