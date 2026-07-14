"""LangGraph 主图 —— 面试业务流程编排。

主图负责固定业务流程（基于 LangGraph 状态机）：
1. ReAct 采集（自循环）：Agent 推理 → 校验 → 信息不足则追问重试
2. 第 1 题：生成首道面试题
3. 第 2~9 题：用户作答后生成下一题
4. 第 10 题答完：生成最终评分报告

架构分层：
- ReAct 采集：LangChain create_agent + 外置 Tool（react_graph.py 内部封装）
  主图只需调用 run_react_agent_step()，根据返回的 react_retry 决定自循环还是前进
- 面试流程：LangGraph 状态机强约束，10 题严格交付
"""

from __future__ import annotations

import logging
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agent.react_graph import run_react_agent_step
from app.agent.state import InterviewState
from app.llm.deepseek import create_deepseek_llm
from app.rag.retriever import get_retriever

logger = logging.getLogger(__name__)

# ==================== LLM 实例（面试出题/评分专用） ====================
_interview_llm = create_deepseek_llm(temperature=0.4)


# ==================== RAG 检索 ====================

async def _search_knowledge(job_text: str) -> str:
    """根据岗位 JD 检索对应面试题库。"""
    try:
        retriever = get_retriever()
        results = await retriever.retrieve(query=job_text, top_k=3)
        if results:
            return "\n".join([r.get("content", "")[:500] for r in results[:3]])
    except Exception as e:
        logger.warning("RAG 检索失败: %s", e)
    return "未检索到相关知识，请基于岗位 JD 和 LLM 自身知识出题。"


# ==================== 主图节点 ====================

async def _run_react_agent_node(state: InterviewState) -> dict:
    """调用 ReAct Agent 采集岗位信息。

    核心 ReAct 循环机制：
    - 每次调用 run_react_agent_step() 为一步推理
    - 如果上次有 tip_msg（追问），传入 previous_tip 续写上下文
    - step 返回 react_retry=True 时，主图自循环回到本节点
    - 用户下一轮输入（补充信息）触发再次推理，直到采集成功

    main_graph 无需感知 Agent 内部怎么推理，只需关注 react_retry。
    """
    # 获取上一步的追问提示（自循环时才有值）
    previous_tip = state.get("tip_msg")
    max_loop = state.get("react_max_loop", 2)

    # 调用 ReAct Agent 执行一步推理
    result = await run_react_agent_step(
        user_input=state["user_input"],
        previous_tip=previous_tip,
    )

    # 清理状态：准备写入本轮结果
    update = {
        "tip_msg": None,
        "react_retry": False,
    }

    if result.get("react_retry"):
        # 信息不足，写入追问提示，等待用户补充后再循环
        update["tip_msg"] = result["tip_msg"]
        update["react_retry"] = True
    else:
        # 采集成功，写入岗位信息
        update["job_info"] = result["job_info"]

    # 追加推理历史（Annotated[List, operator.add] 会自动拼接）
    if result.get("react_history"):
        update["react_history"] = result["react_history"]

    return update


async def _gen_first_question_node(state: InterviewState) -> dict:
    """生成第 1 道面试题（基于采集到的岗位 JD + RAG 知识）。"""
    job_jd = state["job_info"]
    rag_data = await _search_knowledge(job_jd)

    prompt = f"""岗位 JD：{job_jd}

匹配面试题库：{rag_data}

请仅输出 1 道贴合该岗位的专业技术面试题，不要多余描述。"""
    question = (await _interview_llm.ainvoke(prompt)).content.strip()

    return {
        "rag_knowledge": rag_data,
        "question_list": [question],
        "current_round": 1,
    }


async def _gen_next_question_node(state: InterviewState) -> dict:
    """生成第 2~9 道面试题（根据历史题目和用户回答深度生成）。"""
    history_questions = state.get("question_list", [])
    user_answer = state["user_input"]
    job_jd = state["job_info"]
    rag_data = state.get("rag_knowledge", "")

    prompt = f"""岗位 JD：{job_jd}

相关知识：{rag_data}

已出过的题目（禁止重复考点）：
{chr(10).join(f"- {q}" for q in history_questions)}

考生上一轮回答：{user_answer}

根据回答深度生成 1 道全新技术面试题，只输出题目。"""
    new_q = (await _interview_llm.ainvoke(prompt)).content.strip()

    return {
        "question_list": [new_q],
        "answer_list": [user_answer],
        "current_round": state["current_round"] + 1,
    }


async def _generate_score_report_node(state: InterviewState) -> dict:
    """十题全部答完，生成最终评分报告。"""
    user_answer = state["user_input"]
    qa_pairs: list[str] = []
    question_list = state.get("question_list", [])
    all_answers = list(state.get("answer_list", [])) + [user_answer]

    for idx in range(len(question_list)):
        q = question_list[idx] if idx < len(question_list) else "未知题目"
        a = all_answers[idx] if idx < len(all_answers) else "未作答"
        qa_pairs.append(f"第{idx+1}题：{q}\n考生回答：{a}\n---")

    prompt = f"""岗位 JD：{state['job_info']}

考生全部答题记录：
{chr(10).join(qa_pairs)}

请生成完整面试评分报告，包含：
1. 总分（0-100）
2. 每题点评
3. 优势
4. 薄弱点
5. 招聘录用建议"""

    report = (await _interview_llm.ainvoke(prompt)).content.strip()
    return {"final_report": report, "current_round": 10}


# ==================== 主图路由 ====================

def _after_react_route(
    state: InterviewState,
) -> Literal["run_react_agent_node", "gen_first_question_node"]:
    """ReAct 采集节点后路由（自循环核心）。

    - react_retry=True → 回到自身节点，等待用户下一轮输入后再次推理
    - job_info 有值 → 进入出题节点

    完整自循环流程：
    用户输入 → react_agent → 信息不足 → END(暂停) → 用户补充 → react_agent → ... → 成功 → gen_first_question
    """
    if state.get("react_retry"):
        return "run_react_agent_node"
    return "gen_first_question_node"


def _main_graph_route(
    state: InterviewState,
) -> Literal["gen_next_question_node", "generate_score_report_node"]:
    """主流程路由：第 1~9 轮走下一题，第 10 轮生成报告。"""
    round_num = state.get("current_round", 0)
    if 1 <= round_num <= 9:
        return "gen_next_question_node"
    elif round_num >= 10:
        return "generate_score_report_node"
    return "gen_next_question_node"


# ==================== 构建主图 ====================

def build_main_graph() -> StateGraph:
    """构建完整面试主图。

    主图节点链路：
    run_react_agent_node ──(自循环)──→ run_react_agent_node
        │
        └──(成功)──→ gen_first_question_node
                        └──→ gen_next_question_node (1~9轮)
                                └──→ generate_score_report_node → END

    Returns:
        已编译的主图，包含 checkpointer 支持多轮会话持久化。
    """
    graph = StateGraph(InterviewState)

    # 注册节点
    graph.add_node("run_react_agent_node", _run_react_agent_node)
    graph.add_node("gen_first_question_node", _gen_first_question_node)
    graph.add_node("gen_next_question_node", _gen_next_question_node)
    graph.add_node("generate_score_report_node", _generate_score_report_node)

    # 主流程链路
    graph.set_entry_point("run_react_agent_node")

    # ReAct 采集：自循环（信息不足 → END → 用户补充 → 回到自身）或前进
    graph.add_conditional_edges(
        "run_react_agent_node",
        _after_react_route,
        {
            "run_react_agent_node": "run_react_agent_node",
            "gen_first_question_node": "gen_first_question_node",
        },
    )

    # 第1题 → 第2题
    graph.add_conditional_edges(
        "gen_first_question_node",
        _main_graph_route,
        {"gen_next_question_node": "gen_next_question_node"},
    )

    # 第2~9题循环
    graph.add_conditional_edges(
        "gen_next_question_node",
        _main_graph_route,
        {
            "gen_next_question_node": "gen_next_question_node",
            "generate_score_report_node": "generate_score_report_node",
        },
    )

    # 评分报告 → 结束
    graph.add_edge("generate_score_report_node", END)

    # 持久化会话记忆
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


# 全局主图实例（单例）
_main_interview_graph = build_main_graph()
