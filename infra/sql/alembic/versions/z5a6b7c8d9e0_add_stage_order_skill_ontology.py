"""add stage ordering, skill table, ontology tables

Revision ID: z5a6b7c8d9e0
Revises: y4z5a6b7c8d9
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "z5a6b7c8d9e0"
down_revision = "y4z5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # v0.51.5: Stage conditional execution
    op.add_column("pipeline_stage_config", sa.Column("execution_order", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("pipeline_stage_config", sa.Column("condition", postgresql.JSONB(), nullable=True))

    # v0.51.6: Skill table
    op.create_table(
        "skill",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage_name", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("prompt_template", sa.Text, nullable=False),
        sa.Column("input_schema", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("output_schema", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_skill_project", "skill", ["project_id"])

    # v0.51.9: Ontology tables
    op.create_table(
        "ontology_concept",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("definition", sa.Text, nullable=True),
        sa.Column("concept_type", sa.String(50), nullable=False, server_default="entity"),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ontology_concept.id"), nullable=True),
        sa.Column("properties", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ontology_concept_project", "ontology_concept", ["project_id"])

    op.create_table(
        "ontology_relation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("project.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_concept_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ontology_concept.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_concept_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ontology_concept.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ontology_relation_project", "ontology_relation", ["project_id"])


def downgrade() -> None:
    op.drop_table("ontology_relation")
    op.drop_table("ontology_concept")
    op.drop_table("skill")
    op.drop_column("pipeline_stage_config", "condition")
    op.drop_column("pipeline_stage_config", "execution_order")
