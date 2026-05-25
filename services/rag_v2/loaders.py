from __future__ import annotations

from pathlib import Path

from .schema import RagDocument, infer_source_meta


SUPPORTED_EXTENSIONS = {".txt", ".md"}


def iter_rag_files(data_dir: Path) -> list[Path]:
    if not data_dir.exists():
        return []
    return [
        path
        for path in sorted(data_dir.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


def load_documents(data_dir: Path) -> list[RagDocument]:
    documents: list[RagDocument] = []
    for path in iter_rag_files(data_dir):
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            continue
        documents.append(
            RagDocument(
                path=path,
                text=text,
                meta=infer_source_meta(path),
            )
        )
    return documents
