# Cycle 07 — UML-informed activity flow, bounded and evidence-first

## Scope
Keep FastAPI, existing SVG UI, single Snapshot/evidence graph and System → Process → Code navigation.
Integrate the unpushed 0.3.1/0.3.2 reliability fixes only after comparing the remote base.
Implement the first UML slice: distinguish dependency/call/control-flow, and provide an optional activity view for supported function/route bodies. No Sequence/Class/Deployment generator, no XMI/UML conformance claim.

## Acceptance (written before implementation)
- if/elif/else decisions have true/false guards. Only surviving branches merge.
- return and raise/throw go to distinct normal/exception exits, never to the next action.
- A return/throw in BOTH branches leaves subsequent text unreachable; source-order view remains available.
- Python AST: simple statements, if/else, return, raise; reject loops, try/finally, with, match, yield and unsupported embedded control structures for the whole activity (no fabricated bypass).
- JS/TS/Dart: conservative balanced-delimiter subset only; explicit semicolon statements and if/else blocks/inline exits. Unsupported/ambiguous grammar fails closed to the existing source-order view.
- Unmodeled implicit exceptions, short-circuit evaluation, async scheduling and external effects are explicit assumptions; no runtime trace claims.
- Every activity node and edge references the existing evidence registry, flow and file membership. Synthesized control nodes are marked. Canonical source-order steps are NOT replaced.
- Activity solid arrows express control flow; uncertainty is a separate badge, not overloaded UML line style.
- UI remains incremental: an Activity tab, source-order fallback, existing evidence/callee/back navigation and export.
- Test RED → minimal implementation → fresh full tests, JS/Skills, actual HTTP and browser attempts; stop on environment policy blocks, no bridge bypass.
- Only after the verification loop: commit/push authorized changes, no forced update, no target-code execution, paid AI, deployment or workflow permission escalation.

## Sources consulted
- https://www.omg.org/spec/UML/2.5.1/About-UML (specification identity; not a conformance certificate)
- https://plantuml.com/activity-diagram-beta (decisions and branch termination; no engine/code integration)
- https://docs.python.org/3.13/library/ast.html (If/Return/Raise node structure)
