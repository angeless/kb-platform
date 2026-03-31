"""Export service: generate Markdown, PDF, and DOCX files for documents."""

from __future__ import annotations

import io
import re
import uuid
import zipfile

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared_errors import AppException, ErrorCode, NotFoundException
from shared_models import KnowledgeDoc, KnowledgeDocVersion

from . import TenantService


def _safe_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = name.strip(". ")
    return name[:200] or "untitled"


# ---------------------------------------------------------------------------
# Markdown → PDF conversion
# ---------------------------------------------------------------------------

_PDF_CSS = """
@page { size: A4; margin: 2cm; }
body { font-family: "Noto Sans CJK SC", "Noto Sans SC", "PingFang SC",
       "Microsoft YaHei", "Helvetica Neue", Arial, sans-serif;
       font-size: 11pt; line-height: 1.6; color: #333; }
h1 { font-size: 22pt; border-bottom: 1px solid #ddd; padding-bottom: 6px; }
h2 { font-size: 17pt; }
h3 { font-size: 14pt; }
code { font-family: "Fira Code", "Courier New", monospace;
       background: #f5f5f5; padding: 2px 4px; border-radius: 3px; font-size: 10pt; }
pre { background: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
th { background: #f0f0f0; }
blockquote { border-left: 4px solid #ddd; margin: 1em 0; padding: 0.5em 1em; color: #666; }
"""


def convert_md_to_pdf(content_md: str, title: str = "") -> bytes:
    """Convert Markdown text to PDF bytes using weasyprint."""
    import markdown
    from weasyprint import HTML

    html_body = markdown.markdown(
        content_md,
        extensions=["tables", "fenced_code", "codehilite", "toc"],
    )
    full_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>{title}</title>
<style>{_PDF_CSS}</style></head>
<body>{html_body}</body></html>"""

    return HTML(string=full_html).write_pdf()


# ---------------------------------------------------------------------------
# Markdown → DOCX conversion
# ---------------------------------------------------------------------------


def convert_md_to_docx(content_md: str, title: str = "") -> bytes:
    """Convert Markdown text to DOCX bytes using python-docx."""
    import markdown
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # Set default font for CJK compatibility
    style = doc.styles["Normal"]
    font = style.font
    font.size = Pt(11)
    font.name = "Arial"

    if title:
        heading = doc.add_heading(title, level=0)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Parse markdown to simple structure and build docx
    # We use a line-by-line approach for basic markdown elements
    lines = content_md.split("\n")
    in_code_block = False
    code_lines: list[str] = []

    for line in lines:
        # Code block toggling
        if line.strip().startswith("```"):
            if in_code_block:
                # End code block
                code_text = "\n".join(code_lines)
                p = doc.add_paragraph()
                run = p.add_run(code_text)
                run.font.name = "Courier New"
                run.font.size = Pt(9)
                run.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
                p.paragraph_format.left_indent = Pt(18)
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        stripped = line.strip()

        # Empty line
        if not stripped:
            continue

        # Headings
        if stripped.startswith("######"):
            doc.add_heading(stripped[6:].strip(), level=6)
        elif stripped.startswith("#####"):
            doc.add_heading(stripped[5:].strip(), level=5)
        elif stripped.startswith("####"):
            doc.add_heading(stripped[4:].strip(), level=4)
        elif stripped.startswith("###"):
            doc.add_heading(stripped[3:].strip(), level=3)
        elif stripped.startswith("##"):
            doc.add_heading(stripped[2:].strip(), level=2)
        elif stripped.startswith("#"):
            doc.add_heading(stripped[1:].strip(), level=1)
        # Blockquote
        elif stripped.startswith(">"):
            p = doc.add_paragraph(stripped[1:].strip())
            p.paragraph_format.left_indent = Pt(36)
            p.runs[0].font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        # Unordered list
        elif stripped.startswith("- ") or stripped.startswith("* "):
            doc.add_paragraph(stripped[2:], style="List Bullet")
        # Ordered list
        elif re.match(r"^\d+\.\s", stripped):
            text = re.sub(r"^\d+\.\s", "", stripped)
            doc.add_paragraph(text, style="List Number")
        # Regular paragraph
        else:
            doc.add_paragraph(stripped)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# ExportService
# ---------------------------------------------------------------------------


class ExportService(TenantService):
    """Export knowledge documents as Markdown, PDF, DOCX, or ZIP."""

    async def _get_doc_content(self, doc_id: uuid.UUID) -> tuple[KnowledgeDoc, str]:
        """Load a doc and its latest version content. Raises NotFoundException if missing."""
        q = select(KnowledgeDoc).where(KnowledgeDoc.id == doc_id)
        result = await self.db.execute(q)
        doc = result.scalar_one_or_none()
        if doc is None:
            raise NotFoundException(error_code=ErrorCode.DOC_NOT_FOUND, message="文档不存在")
        await self._verify_project(doc.project_id)

        ver_q = select(KnowledgeDocVersion).where(
            KnowledgeDocVersion.doc_id == doc_id,
        ).order_by(KnowledgeDocVersion.version.desc()).limit(1)
        ver = (await self.db.execute(ver_q)).scalar_one_or_none()

        content = ver.content_md if ver else ""
        return doc, content

    async def export_single_doc(
        self, doc_id: uuid.UUID, fmt: str = "markdown"
    ) -> tuple[str, str | bytes, str]:
        """Export a single doc. Returns (filename, content, media_type)."""
        doc, content = await self._get_doc_content(doc_id)
        safe_title = _safe_filename(doc.title)

        if fmt == "pdf":
            try:
                pdf_bytes = convert_md_to_pdf(content, title=doc.title)
            except Exception as e:
                raise AppException(
                    ErrorCode.SYSTEM_INTERNAL_ERROR,
                    f"PDF 转换失败: {e}",
                    status_code=500,
                )
            return (
                f"{safe_title}.pdf",
                pdf_bytes,
                "application/pdf",
            )

        if fmt == "docx":
            try:
                docx_bytes = convert_md_to_docx(content, title=doc.title)
            except Exception as e:
                raise AppException(
                    ErrorCode.SYSTEM_INTERNAL_ERROR,
                    f"DOCX 转换失败: {e}",
                    status_code=500,
                )
            return (
                f"{safe_title}.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

        # Default: markdown
        return f"{safe_title}.md", content, "text/markdown; charset=utf-8"

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
