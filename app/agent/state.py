"""LangGraph 统一 State —— 主图共享上下文。"""

from __future__ import annotations

import operator
from typing import Annotated, List, Optional, TypedDict


class InterviewState(TypedDict):
    """面试全局状态。

    主图各节点共享同一套 State，支持 ReAct 自循环追问和多轮面试。
    """

    # ---- 会话基础 ----
    thread_id: str
    user_input: str                  # 用户本轮输入

    # ---- 岗位信息采集（ReAct 产出） ----
    job_info: Optional[str]          # 最终有效岗位文本
    react_max_loop: int              # ReAct 最大循环次数，防死循环
    react_retry: bool                # 信息不足时，主图自循环重试标志
    react_history: Annotated[List[str], operator.add]  # ReAct 每轮思考/观测记录

    # ---- 面试业务流程 ----
    rag_knowledge: Optional[str]     # RAG 检索到的面试题库
    question_list: Annotated[List[str], operator.add]  # 已生成题目
    answer_list: Annotated[List[str], operator.add]    # 用户作答
    current_round: int               # 0=待采集岗位；1~10=面试答题
    final_report: Optional[str]      # 最终评分报告
    tip_msg: Optional[str]           # 提示文案（采集失败 / 补充输入）
    error: Optional[str]             # 错误信息
