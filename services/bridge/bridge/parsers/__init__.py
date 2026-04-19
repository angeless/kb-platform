"""Bridge file parsers.

Each parser converts a source file into the canonical IR (intermediate
representation) used by the bridge_ingest pipeline stage:

    {
        "kind":          str,      # markdown | docx | pdf | image | ...
        "title":         str,
        "content_md":    str,      # canonical markdown body (no frontmatter)
        "frontmatter":   dict,     # parsed YAML frontmatter (may be empty)
        "wiki_links":    list[str],# [[wiki/...]] references found in body
        "outbound_urls": list[str],# external http(s) URLs in body
        "raw_size":      int,      # original file size in bytes
        "content_hash":  str,      # sha256 of canonical content_md
        "source_path":   str,      # absolute path to source file
        "source_format": str,      # original file extension w/o dot
    }

Parsers are pure functions (no DB writes). The bridge_ingest stage
consumes the IR and persists Asset/AssetChunk rows.
"""
