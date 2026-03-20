"""Export service: generate Markdown files and ZIP archives for documents."""

from __future__ import annotations

import io
import re
import uuid
import zipfile

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import ErrorCode, NotFoundException
from shared_models import KnowledgeDoc, KnowledgeDocVersion

from . import TenantService


def _safe_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = name.strip(". ")
    return name[:200] or "untitled"


class ExportService(TenantService):
    """Export knowledge documents as Markdown or ZIP."""

    async def export_single_doc(self, doc_id: uuid.UUID) -> tuple[str, str]:
        """Export a single doc as Markdown. Returns (filename, content)."""
        q = select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        result = await self.db.execute(q)
        doc = result.scalar_one_or_none()
        if doc is None:
            raise NotFoundException(error_code=ErrorCode.DOC_NOT_FOUND, message="文档不存在")
        await self._verify_project(doc.project_id)

        # Get latest version
        ver_q = select(KnowledgeDocVersion).where(
            KnowledgeDocVersion.doc_id == doc_id,
        ).order_by(KnowledgeDocVersion.version.desc()).limit(1)
        ver = (await self.db.execute(ver_q)).scalar_one_or_none()

        content = ver.content_md if ver else ""
        filename = f"{_safe_filename(doc.title)}.md"
        return filename, content

    async def export_project_zip(self, project_id: uuid.UUID) -> tuple[str, bytes]:
        """Export all docs in a project as a ZIP. Returns (zip_filename, zip_bytes)."""
        project = await self._verify_project(project_id)

        docs_q = select(KnowledgeDoc).where(KnowledgeDoc.project_id == project_id)
        docs = (await self.db.execute(docs_q)).scalars().all()

        buf = io.BytesIO()
        project_dir = _safe_filename(project.name)

        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            index_lines = [f"# {project.name} 知识文档目录\n"]

            for doc in docs:
                # Get latest version
                ver_q = select(KnowledgeDocVersion).where(
                    KnowledgeDocVersion.doc_id == doc.id,
                ).order_by(KnowledgeDocVersion.version.desc()).limit(1)
                ver = (await self.db.execute(ver_q)).scalar_one_or_none()

                content = ver.content_md if ver else ""
                safe_title = _safe_filename(doc.title)
                doc_path = f"{project_dir}/{doc.doc_type}/{safe_title}.md"
                zf.writestr(doc_path, content)
                index_lines.append(f"- [{doc.title}]({doc.doc_type}/{safe_title}.md) ({doc.status})")

            zf.writestr(f"{project_dir}/index.md", "\n".join(index_lines))

        zip_filename = f"{_safe_filename(project.name)}.zip"
        return zip_filename, buf.getvalue()
