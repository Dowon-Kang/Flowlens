# Cycle 06 — evidence provenance and honest coverage

Base: attached v0.3.1 local ZIP. No remote writes, paid calls, target execution,
framework migration, security-policy changes, or browser-policy bypass.

## Acceptance before implementation

1. Python call exploration follows explicit imports (including module aliases),
   nearest lexical definitions and shadowing. Ambiguous/reassigned/parameter
   targets stay unresolved. Record a reason; never claim compiler precision.
2. A missing/invalid Python parse is not called full analysis merely because the
   file was read. JSON and the existing coverage panel distinguish read coverage,
   AST/lexical coverage, parse failures and unresolved extracted calls. Metrics
   are counts, not a reliability probability or a completeness percentage.
3. GitHub applies the same metadata selection plan as folder/ZIP before blob
   reads, including the 2 MiB total budget. No source-count/secret limits relaxed.
   Transport mocks are not called live GitHub verification.
4. Exact Python HTTP call positions cannot transfer network evidence to a
   same-named non-HTTP call on the same source line.
5. Tests first, baseline and red logs retained; then pytest, JS, skills,
   verify.py --browser. A blocked/missing browser is recorded, never bypassed.

## Upstream design references checked 2026-10-06

- CodeBoarding (official engine README): static extraction separate from model
  description; one analysis.json and nested source-backed maps.
  https://github.com/CodeBoarding/CodeBoarding
- Sourcegraph docs: precise/indexed and syntax/search navigation are different.
  https://sourcegraph.com/docs/code-navigation
- AWS Labs codeknit: retain unresolved/ambiguous relationships and diagnostics;
  tested capability matrix and partial outputs, not an unqualified success.
  https://github.com/awslabs/codeknit
- Aider repo map: rank relevant graph portions within a budget.
  https://aider.chat/docs/repomap.html

Adopt design principles, not third-party source code or packages. SCIP/LSP,
Tree-sitter, graph ranking and agent swarms are not installed in this cycle.
Graph ranking needs actual graph evidence and must not be faked by filename scores.
