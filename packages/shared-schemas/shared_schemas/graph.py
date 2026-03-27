"""Graph visualization schemas."""

from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    label: str
    node_type: str  # "doc"
    node_path: list[str]
    status: str


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
