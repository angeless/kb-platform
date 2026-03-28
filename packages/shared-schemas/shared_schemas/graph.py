"""Graph visualization schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str = Field(max_length=500)
    node_type: Literal["doc"] = "doc"
    node_path: list[str]
    status: Literal["approved", "draft"]


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    edge_type: str  # "cross_ref" or "parent_child"
    relation_type: str | None = None


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    node_count: int
    edge_count: int
