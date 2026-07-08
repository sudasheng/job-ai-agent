"""文档加载器 —— 将各种格式的文档加载并切分为可索引的文本块。"""

from __future__ import annotations

import logging
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)


class DocumentLoader:
    """通用文档加载器。

    支持：
    - 纯文本
    - 岗位描述 JSON
    - Markdown 文档
    - 后续可扩展：PDF、HTML 等
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", ".", " ", ""],
            length_function=len,
        )

    def load_text(self, text: str, metadata: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """加载纯文本并切分为块。"""
        chunks = self._splitter.split_text(text)
        return [
            {"content": chunk, "metadata": metadata or {}}
            for chunk in chunks
        ]

    def load_job(self, job: dict[str, Any]) -> list[dict[str, Any]]:
        """加载岗位信息，构建结构化文本并切分。"""
        text_parts = [
            f"岗位名称: {job.get('title', '')}",
            f"公司名称: {job.get('company_name', '')}",
            f"工作城市: {job.get('city', '')}",
            f"经验要求: {job.get('experience', '')}",
            f"学历要求: {job.get('education', '')}",
            f"薪资范围: {job.get('salary_desc', '')}",
            f"岗位描述: {job.get('job_description', '')}",
            f"岗位要求: {job.get('job_requirements', '')}",
        ]
        text = "\n".join(text_parts)
        metadata = {
            "type": "job",
            "job_id": job.get("id", ""),
            "title": job.get("title", ""),
            "company": job.get("company_name", ""),
            "city": job.get("city", ""),
        }
        return self.load_text(text, metadata)

    def load_interview_qa(
        self,
        question: str,
        answer: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """加载面试问答对。"""
        text = f"面试问题: {question}\n参考答案: {answer}"
        return self.load_text(text, metadata or {"type": "interview_qa"})


_document_loader: DocumentLoader | None = None


def get_document_loader() -> DocumentLoader:
    """获取文档加载器单例。"""
    global _document_loader
    if _document_loader is None:
        _document_loader = DocumentLoader()
    return _document_loader