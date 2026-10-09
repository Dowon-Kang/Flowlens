from __future__ import annotations
from typing import Literal
from . import __version__
from pydantic import BaseModel, ConfigDict, Field

class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")

class SourceFile(Model):
    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=65536)

class FileMetadata(Model):
    path: str = Field(min_length=1, max_length=240)
    size: int = Field(ge=0, le=2**53-1, strict=True)

class FilePlanRequest(Model):
    entries: list[FileMetadata] = Field(max_length=2500)

class ReadFailure(Model):
    path: str = Field(min_length=1, max_length=240)
    reason: Literal["invalid_text", "read_error"]

class BrowserSelection(Model):
    reported_by: Literal["browser"] = "browser"
    discovered: int
    transmitted: int
    skipped: int
    omitted: int
    failed: int
    reason_counts: dict[str, int]

class AnalyzeRequest(Model):
    source: Literal["demo", "github", "files"] = "demo"
    demo: Literal["mobile", "python"] = "mobile"
    url: str = Field(default="", max_length=500)
    files: list[SourceFile] = Field(default_factory=list, max_length=1000)
    explain: bool = False
    manifest: list[FileMetadata] | None = Field(default=None, max_length=2500)
    read_failures: list[ReadFailure] = Field(default_factory=list, max_length=160)

class Coverage(Model):
    discovered: int = 0
    eligible: int = 0
    analyzed: int = 0
    skipped: int = 0
    omitted: int = 0
    failed: int = 0
    bytes_read: int = 0
    partial: bool = False
    tree_truncated: bool = False
    reason_counts: dict[str, int] = Field(default_factory=dict)
    browser_selection: BrowserSelection | None = None
    notes: list[str] = Field(default_factory=list)

class Snapshot(Model):
    name: str
    source: str
    revision: str
    repository_url: str = ""
    files: list[SourceFile]
    coverage: Coverage
    warnings: list[str] = Field(default_factory=list)

class Evidence(Model):
    id: str
    path: str
    line: int
    end_line: int
    snippet: str
    kind: str
    parser: Literal["ast", "lexical", "manifest"]
    url: str = ""

class Fact(Model):
    path: str
    kind: Literal["import", "route", "request", "symbol", "config-url"]
    value: str
    evidence_id: str
    method: str = ""
    target: str = ""

class Node(Model):
    id: str
    label: str
    kind: Literal["file", "infrastructure", "component", "virtual"]
    component_id: str = ""
    role: str
    description: str
    evidence_ids: list[str] = Field(default_factory=list)
    member_ids: list[str] = Field(default_factory=list)
    path: str = ""
    tags: list[str] = Field(default_factory=list)

class Edge(Model):
    relationship_kind: Literal["dependency", "reference"] = "dependency"
    id: str
    source: str
    target: str
    relation: str
    confidence: Literal["confirmed", "candidate"]
    evidence_ids: list[str]
    description: str

class AnalysisDiagnostic(Model):
    code: str
    severity: Literal["info", "warning"]
    path: str = ""
    message: str

class AnalysisQuality(Model):
    scope: Literal["selected-source-files"] = "selected-source-files"
    source_files: int = Field(default=0, ge=0)
    manifest_files: int = Field(default=0, ge=0)
    ast_files: int = Field(default=0, ge=0)
    lexical_files: int = Field(default=0, ge=0)
    parse_failed_files: int = Field(default=0, ge=0)
    process_flows: int = Field(default=0, ge=0)
    calls: int = Field(default=0, ge=0)
    static_candidate_calls: int = Field(default=0, ge=0)
    unresolved_calls: int = Field(default=0, ge=0)
    unknown_steps: int = Field(default=0, ge=0)
    runtime_verified: Literal[False] = False

class CallSite(Model):
    offset: int = -1
    relation: Literal["call"] = "call"
    name: str
    evidence_id: str
    resolution_basis: Literal["unresolved", "python-local", "python-import", "lexical"] = "unresolved"
    resolution_reason: str = ""
    callee_id: str = ""
    resolution: Literal["unresolved", "static-candidate"] = "unresolved"

class ProcessStep(Model):
    id: str
    label: str
    category: str
    line: int
    end_line: int
    evidence_ids: list[str]
    node_ids: list[str]
    calls: list[CallSite] = Field(default_factory=list)
    conditional: bool = False
    semantic_status: Literal["syntax", "candidate", "unknown"] = "candidate"
    description: str = "식별자·문장 형태 기반 요약 후보 · 실제 실행 미검증"

class ActivityCallRef(Model):
    step_id: str
    call_index: int = Field(ge=0)

class ActivityNode(Model):
    offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    call_refs: list[ActivityCallRef] = Field(default_factory=list)
    id: str
    kind: Literal["initial", "action", "decision", "merge", "return", "raise", "final", "exception-final"]
    label: str
    line: int
    end_line: int
    node_ids: list[str]
    evidence_ids: list[str]
    step_ids: list[str] = Field(default_factory=list)
    synthetic: bool = False
    semantic_status: Literal["syntax", "candidate", "unknown"] = "unknown"

class ActivityEdge(Model):
    id: str
    source: str
    target: str
    relation: Literal["control-flow"] = "control-flow"
    confidence: Literal["static-candidate"] = "static-candidate"
    guard: Literal["", "true", "false"] = ""
    evidence_ids: list[str]

class ActivityFlow(Model):
    status: Literal["supported-subset", "unsupported"]
    parser: Literal["python-ast", "lexical-subset"]
    reason: str = ""
    nodes: list[ActivityNode] = Field(default_factory=list)
    edges: list[ActivityEdge] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    runtime_verified: Literal[False] = False
    semantics: Literal["explicit-branch-control-flow"] = "explicit-branch-control-flow"

class ProcessFlow(Model):
    activity: ActivityFlow | None = None
    id: str
    label: str
    path: str
    line: int
    end_line: int
    kind: Literal["route", "function", "sdk"]
    node_ids: list[str]
    evidence_ids: list[str]
    steps: list[ProcessStep]
    order: Literal["source-order"] = "source-order"
    warnings: list[str] = Field(default_factory=list)

class Feature(Model):
    flow_ids: list[str] = Field(default_factory=list)
    id: str
    label: str
    description: str
    endpoint_labels: list[str]
    node_ids: list[str]
    edge_ids: list[str]
    component_ids: list[str]
    warnings: list[str] = Field(default_factory=list)

class StageRecord(Model):
    name: str
    status: Literal["passed", "skipped", "warning"]
    duration_ms: int
    detail: str

class NodeExplanation(Model):
    node_id: str
    summary: str = Field(max_length=600)
    evidence_ids: list[str] = Field(max_length=12)

class Explanation(Model):
    summary: str = Field(max_length=1600)
    node_summaries: list[NodeExplanation] = Field(max_length=12)

class Analysis(Model):
    analysis_quality: AnalysisQuality | None = None
    diagnostics: list[AnalysisDiagnostic] = Field(default_factory=list)
    flows: list[ProcessFlow] = Field(default_factory=list)
    schema_version: str = "1.2"
    analyzer_version: str = __version__
    name: str
    source: str
    revision: str
    repository_url: str
    coverage: Coverage
    nodes: list[Node]
    edges: list[Edge]
    system_nodes: list[Node]
    system_edges: list[Edge]
    features: list[Feature]
    evidence: list[Evidence]
    facts: list[Fact]
    warnings: list[str]
    stages: list[StageRecord] = Field(default_factory=list)
    explanation: Explanation | None = None
    summary: str = ""
