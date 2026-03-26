import json
from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db, AsyncSessionLocal
from src.api.dependencies import get_current_user
from src.models.user import User, Profile
from src.models.agent import AgentTuning, UserMemoryInsight
from src.schemas.agent_chat import ChatRequest
from src.core.ai_engine import (
    client, build_system_prompt, retrieve_long_term_memory, 
    get_short_term_memory, compress_context, create_embedding, 
    save_conversation_to_memory, extract_and_store_memory
)

from src.skills.registry import agent_skills
import src.skills.knowledge_base

router = APIRouter()

@router.post("/chat")
async def chat_with_agent(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """AI 智能体核心对话流 (支持 SSE, RAG, 动态 Skill Loop)"""
    
    # 1. 提取动态总结的高价值潜意识记忆 (Insight RAG)
    current_msg_vector = await create_embedding(request.message)
    insight_stmt = (
        select(UserMemoryInsight)
        .where(UserMemoryInsight.user_id == current_user.id)
        .order_by(UserMemoryInsight.embedding.cosine_distance(current_msg_vector))
        .limit(3)
    )
    memory_results = (await db.execute(insight_stmt)).scalars().all()
    memory_insights = [m.insight_text for m in memory_results]
    
    # 2. 组装人设与 System Prompt
    profile = (await db.execute(select(Profile).where(Profile.user_id == current_user.id))).scalars().first()
    tuning = (await db.execute(select(AgentTuning).where(AgentTuning.user_id == current_user.id))).scalars().first()
    system_prompt = build_system_prompt(profile, tuning, memory_insights)
    
    # 3. 原始长期对话切片召回 (保持原逻辑辅助上下文)
    long_term_memories = await retrieve_long_term_memory(db, current_user.id, current_msg_vector)
    if long_term_memories:
        memory_context = "\n".join(long_term_memories)
        system_prompt += f"\n【原始对话片段回忆】：\n{memory_context}"

    # 4. 短期滑动窗口加载与截断限制压缩
    recent_history = await get_short_term_memory(db, current_user.id, limit=6)
    raw_messages = [{"role": "system", "content": system_prompt}] + recent_history + [{"role": "user", "content": request.message}]
    messages = compress_context(raw_messages, max_tokens=8000)

    # 获取注册表中的可用技能 Schema
    tools_schema = agent_skills.get_tools_schema()
    tools_payload = tools_schema if tools_schema else None

    # 5. SSE 异步生成器与 Skill 调用循环 (Agentic Loop)
    async def event_generator():
        nonlocal messages
        full_ai_response = ""
        
        while True: # Agent 工作流引擎循环
            stream = await client.chat.completions.create(
                model="gpt-4o-mini", # 或 deepseek-chat
                messages=messages,
                tools=tools_payload,
                stream=True
            )
            
            is_tool_call = False
            tool_call_name = ""
            tool_call_args = ""
            tool_call_id = ""

            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                
                # A. 模型决定调用工具
                if delta.tool_calls:
                    is_tool_call = True
                    tc = delta.tool_calls[0]
                    if tc.id: tool_call_id = tc.id
                    if tc.function.name: tool_call_name = tc.function.name
                    if tc.function.arguments: tool_call_args += tc.function.arguments
                    continue
                
                # B. 流式输出正常文本
                if delta.content:
                    text_chunk = delta.content
                    full_ai_response += text_chunk
                    yield f"data: {json.dumps({'content': text_chunk, 'done': False}, ensure_ascii=False)}\n\n"

            # 执行 Skill 技能拦截
            if is_tool_call:
                # 给前端发送状态打点
                yield f"data: {json.dumps({'tool_call': f'正在检索信息...', 'done': False}, ensure_ascii=False)}\n\n"
                
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{"id": tool_call_id, "type": "function", "function": {"name": tool_call_name, "arguments": tool_call_args}}]
                })
                
                # 动态透传 DB Session 和当前用户给对应的 Skill
                tool_result = await agent_skills.execute_skill(
                    name=tool_call_name, 
                    args_json=tool_call_args,
                    db=db,
                    current_user=current_user
                )
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_call_name,
                    "content": tool_result
                })
                continue 
            
            break # 回复完成，跳出工作流

        yield f"data: {json.dumps({'done': True})}\n\n"
        
        # 6. 生成完毕，触发异步落库与 AI 长期记忆总结任务
        async def background_memory_jobs():
            async with AsyncSessionLocal() as bg_db:
                # a. 保存原始切片以供下次滑动窗口使用
                await save_conversation_to_memory(bg_db, current_user.id, request.message, full_ai_response)
                # b. 高价值事实提炼：剥离噪音，提纯特征入库
                await extract_and_store_memory(bg_db, current_user.id, request.message, full_ai_response)
                
        background_tasks.add_task(background_memory_jobs)

    return StreamingResponse(event_generator(), media_type="text/event-stream")