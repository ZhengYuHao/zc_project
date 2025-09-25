from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table

from sapperrag.model.model import MappedBase

# Association Tables for Many-to-Many relationships
community_entity_map = Table(
    'community_entity_map',
    MappedBase.metadata,
    Column('community_id', ForeignKey('community.id', ondelete='CASCADE'), primary_key=True),
    Column('knowledge_entity_id', ForeignKey('knowledge_entity.id', ondelete='CASCADE'), primary_key=True)
)
