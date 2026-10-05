from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")

class SourceFile(Model):
    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=65536)

class AnalyzeRequest(Model):
    source: Literal["demo", "github", "files"] = "demo"
    demo: Literal["mobile", "python"] = "mobile"
    url: str = Field(default="", max_length=500)
    files: list[SourceFile] = Field(default_factory=list, max_length=1000)
    explain: bool = False

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
    kind: Literal["import", "route", "request", "symbol"]
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
    id: str
    source: str
    target: str
    relation: str
    confidence: Literal["confirmed", "candidate"]
    evidence_ids: list[str]
    description: str

class Feature(Model):
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
    schema_version: str = "1.0"
    analyzer_version: str = "0.2.0"
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
