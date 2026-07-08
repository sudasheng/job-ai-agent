"""应用级自定义异常体系。"""

from __future__ import annotations


class AppException(Exception):
    """应用基础异常。"""

    def __init__(self, message: str = "服务器内部错误", code: int = 500) -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(AppException):
    """资源未找到。"""

    def __init__(self, message: str = "资源未找到") -> None:
        super().__init__(message, code=404)


class UnauthorizedError(AppException):
    """未认证。"""

    def __init__(self, message: str = "未登录或认证已过期") -> None:
        super().__init__(message, code=401)


class ForbiddenError(AppException):
    """无权限。"""

    def __init__(self, message: str = "无权限访问") -> None:
        super().__init__(message, code=403)


class ConflictError(AppException):
    """资源冲突。"""

    def __init__(self, message: str = "资源冲突") -> None:
        super().__init__(message, code=409)


class ValidationError(AppException):
    """参数校验失败。"""

    def __init__(self, message: str = "参数校验失败") -> None:
        super().__init__(message, code=422)


class LLMError(AppException):
    """LLM 调用异常。"""

    def __init__(self, message: str = "大模型调用失败") -> None:
        super().__init__(message, code=502)


class CrawlerError(AppException):
    """爬虫异常。"""

    def __init__(self, message: str = "数据抓取失败") -> None:
        super().__init__(message, code=502)


class RAGError(AppException):
    """RAG 检索异常。"""

    def __init__(self, message: str = "知识检索失败") -> None:
        super().__init__(message, code=502)