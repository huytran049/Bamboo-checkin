from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class DocType(StrEnum):
    FAQ = "faq"
    COMPANY_PROFILE = "company_profile"
    PRODUCT_SOLUTION = "product_solution"
    MANUAL = "manual"
    PROJECT_OVERVIEW = "project_overview"
    SMALL_TALK = "small_talk"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RagSourceMeta:
    source_name: str
    doc_type: DocType
    source_group: str
    product: str
    topic: str
    lang: str = "vi"
    notes: str = ""


@dataclass(frozen=True)
class RagDocument:
    path: Path
    text: str
    meta: RagSourceMeta
    extra: dict[str, str] = field(default_factory=dict)


_SOURCE_META_MAP: dict[str, RagSourceMeta] = {
    "bamboo_faq.txt": RagSourceMeta(
        source_name="bamboo_faq.txt",
        doc_type=DocType.FAQ,
        source_group="bamboo",
        product="bamboo",
        topic="project_faq",
    ),
    "giao_tiep_co_ban.txt": RagSourceMeta(
        source_name="giao_tiep_co_ban.txt",
        doc_type=DocType.SMALL_TALK,
        source_group="qa_assistant",
        product="qa",
        topic="small_talk",
    ),
    "ssg_profile.txt": RagSourceMeta(
        source_name="SSG_profile.txt",
        doc_type=DocType.FAQ,
        source_group="saomai",
        product="saomai",
        topic="company_faq",
    ),
    "jss_profile.txt": RagSourceMeta(
        source_name="JSS_profile.txt",
        doc_type=DocType.FAQ,
        source_group="jss",
        product="jss",
        topic="company_faq",
    ),
    "rag_saomai2.txt": RagSourceMeta(
        source_name="RAG_saomai2.txt",
        doc_type=DocType.COMPANY_PROFILE,
        source_group="saomai",
        product="saomai",
        topic="company_profile",
    ),
    "ecosave.txt": RagSourceMeta(
        source_name="ECOSAVE.txt",
        doc_type=DocType.PRODUCT_SOLUTION,
        source_group="saomai",
        product="ecosave",
        topic="solution_overview",
    ),
    "smart_box.txt": RagSourceMeta(
        source_name="Smart_box.txt",
        doc_type=DocType.PRODUCT_SOLUTION,
        source_group="saomai",
        product="smart_box",
        topic="solution_overview",
    ),
    "camera_ai.txt": RagSourceMeta(
        source_name="camera_AI.txt",
        doc_type=DocType.PRODUCT_SOLUTION,
        source_group="saomai",
        product="camera_ai",
        topic="solution_overview",
    ),
    "inspection_machine.txt": RagSourceMeta(
        source_name="inspection_machine.txt",
        doc_type=DocType.MANUAL,
        source_group="saomai",
        product="inspection_machine",
        topic="user_manual",
    ),
    "bamboo.txt": RagSourceMeta(
        source_name="bamboo.txt",
        doc_type=DocType.PROJECT_OVERVIEW,
        source_group="bamboo",
        product="bamboo",
        topic="project_overview",
    ),
}


def infer_source_meta(path: Path) -> RagSourceMeta:
    key = path.name.lower()
    mapped = _SOURCE_META_MAP.get(key)
    if mapped:
        return mapped
    stem = path.stem.lower()
    return RagSourceMeta(
        source_name=path.name,
        doc_type=DocType.UNKNOWN,
        source_group=stem,
        product=stem,
        topic="unknown",
        notes="Unclassified source. Review before rag_v2 cutover.",
    )
