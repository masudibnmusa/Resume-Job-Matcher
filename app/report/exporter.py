from pathlib import Path

_CSS = (
    "body{font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:860px;margin:2rem auto;"
    "padding:0 1rem;line-height:1.55;color:#222}"
    "table{border-collapse:collapse;width:100%;margin:1rem 0}"
    "th,td{border:1px solid #ddd;padding:6px 10px;text-align:left;vertical-align:top;font-size:.92rem}"
    "th{background:#f5f5f5}blockquote{border-left:4px solid #ccc;margin:1rem 0;padding:.2rem 1rem;color:#555}"
)


def _to_html(md_text: str) -> str:
    import markdown

    body = markdown.markdown(md_text, extensions=["tables"])
    return f"<!doctype html><html><head><meta charset='utf-8'><title>Match Report</title><style>{_CSS}</style></head><body>{body}</body></html>"


def export_report(md_text: str, output_path: str | Path, fmt: str | None = None) -> Path:
    path = Path(output_path)
    fmt = (fmt or path.suffix.lstrip(".") or "md").lower()
    path.parent.mkdir(parents=True, exist_ok=True)

    if fmt in ("md", "markdown"):
        path.write_text(md_text, encoding="utf-8")
    elif fmt == "html":
        path.write_text(_to_html(md_text), encoding="utf-8")
    elif fmt == "pdf":
        try:
            from weasyprint import HTML
        except ImportError as e:
            raise RuntimeError("PDF export needs WeasyPrint: pip install weasyprint") from e
        HTML(string=_to_html(md_text)).write_pdf(str(path))
    else:
        raise ValueError(f"Unsupported format: {fmt} (use md, html, or pdf)")
    return path