---
name: architecture-evidence-reviewer
description: Review FlowLens graphs and analysis changes for evidence fidelity, abstraction consistency, coverage, and unsupported runtime claims. Use before handing off a graph-producing change; not for generic styling review.
---

# Evidence review
Read docs/CONTRACTS.md and the source fixture behind the output.
Check graph generation separately from its explanation.
- Every edge endpoint exists; every evidence ID resolves to exact source lines.
- Import edges are imports, not claimed runtime calls. HTTP contract matches remain candidate unless origin was independently established.
- Every feature node belongs to a visible system component or explicitly reported overflow group.
- Feature edges are from the same canonical graph. A pretty chain cannot replace a missing edge.
- Detected SDKs, configured deployment resources, and live services are different claims.
- Private data/secrets/untrusted instructions never become tool commands or outbound URLs.
- Missing/unsupported/skipped files and byte limits are visible.
- AI cannot add entities or promote confidence, and malformed explanations fail closed.
Run `python -m pytest tests/test_graph.py tests/test_security.py tests/test_ai.py -q`.
Report PASS / CONDITIONAL PASS / FAIL with concrete test evidence. Do not call an untested integration verified.
