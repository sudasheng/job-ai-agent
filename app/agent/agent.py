"""LangChain Agent 主控制器 —— 编排 Skill 执行。"""

from __future__ import annotations

import logging
from typing import Any

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool

from app.llm.deepseek import get_default_llm

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """\
你是求职 AI 助手，能够帮助用户完成以下任务：

1. **岗位搜索**: 根据用户输入的方向/关键词，抓取 Boss 直聘的岗位信息
2. **面试问题生成**: 根据岗位信息或面试方向，生成高质量的面试问题和参考答案
3. **面试评分**: 评估用户的面试回答，给出专业评分和改进建议
4. **AI 聊天**: 回答求职相关的各种问题

请根据用户的需求，选择合适的工具完成任务。
"""


class JobAIAgent:
    """求职 AI Agent。

    使用 LangChain Agent 框架，将各类 Skill 注册为 Tool，
    Agent 根据用户意图自动选择和调用 Tool。
    """

    def __init__(self, tools: list[BaseTool] | None = None) -> None:
        self._llm = get_default_llm()
        self._tools = tools or []

    def register_tool(self, tool: BaseTool) -> None:
        """注册工具。"""
        self._tools.append(tool)

    def register_tools(self, tools: list[BaseTool]) -> None:
        """批量注册工具。"""
        self._tools.extend(tools)

    def create_executor(self) -> AgentExecutor:
        """创建 Agent 执行器。"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", AGENT_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_tools_agent(self._llm, self._tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=self._tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
        )

    async def invoke(self, user_input: str, chat_history: list | None = None) -> dict[str, Any]:
        """执行 Agent 任务。"""
        executor = self.create_executor()
        result = await executor.ainvoke({
            "input": user_input,
            "chat_history": chat_history or [],
        })
        return result

    def get_tools_description(self) -> list[dict[str, str]]:
        """获取所有已注册工具的描述。"""
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools
        ]