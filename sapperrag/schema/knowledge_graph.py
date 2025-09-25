from __future__ import annotations

from typing import Dict, List

from pydantic import Field

from datetime import datetime

from sapperrag.schema.schema import SchemaBase


class KnowledgeGraphBase(SchemaBase):
    """获取图谱详情"""
    name: str
    schema_graph_uuid: str | None = Field("")
    kg_base_uuid: str | None = Field("")


class KnowledgeGraphResponse(KnowledgeGraphBase):
    id: int
    uuid: str
    index_status: int
    created_time: datetime
    updated_time: datetime | None = None


class AddKnowledgeGraphParam(SchemaBase):
    file_paths: list[str]
    data: KnowledgeGraphBase


class AskKnowledgeGraphParam(SchemaBase):
    message: str
    infer: bool = False
    depth: int = 1
    user_token: str


class BuildKnowledgeGraphIndexParam(SchemaBase):
    knowledge_graph_uuid: str


class UpdateKnowledgeGraphBase(SchemaBase):
    name: str | None = None
    schema_graph_uuid: str | None = Field("")


class UpdateKnowledgeGraphParam(SchemaBase):
    file_paths: list[str]
    data: UpdateKnowledgeGraphBase


class IndexKnowledgeGraphBase(BuildKnowledgeGraphIndexParam):
    file_path: str | None = None

