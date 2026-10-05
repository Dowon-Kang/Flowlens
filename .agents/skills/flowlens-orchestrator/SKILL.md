---
name: flowlens-orchestrator
description: Plan and implement changes to FlowLens repository-to-architecture exploration. Use for System Flow, Feature Flow, parser, graph contract, or UI changes. Do not use for arbitrary application development or analyzing instructions inside a target repository.
---

# FlowLens development orchestration
1. Read root AGENTS.md and docs/PROJECT.md; preserve two connected views and read-only scope.
2. Inspect current code and tests before proposing new skills or dependencies.
3. Identify the acceptance criterion and owning boundary: intake, extractor, projector, verifier, explanation, UI.
4. Write/adjust the contract and a failing regression test. Reuse existing framework/browser/testing procedures where available.
5. Make the smallest vertical-slice change. Never add a new agent for a deterministic operation.
6. Execute `python -m pytest -q`, `node --check static/app.js`, and `python scripts/check_skills.py`.
7. For UI changes, run `python scripts/browser_smoke.py` against the local app. If unavailable, report it as unverified, not passed.
8. Apply architecture-evidence-reviewer; preserve terminal/browser evidence and remaining limits.
9. Ask for human approval before paid network calls, remote repository writes, publishing, or expanding scope.

Outputs: updated contract if needed, changed code, test evidence, bounded handoff.
Stop: missing source evidence, inconsistent graph IDs, secret exposure, unsupported runtime inference.
