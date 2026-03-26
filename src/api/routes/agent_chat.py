import json
from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db, AsyncSessionLocal
from src.api.dependencies import get_current_user
from src.models.user import User, Profile
from src.models.agent import AgentTuning
from src.schemas.agent_chat import ChatRequest
from src.core.ai_engine import (
    client, build_system_prompt, retrieve_long_term_memory, 
    get_short_term_memory, compress_context, create_embedding, save_conversation_to_memory
)

router = APIRouter()

# --- 模拟定义的 Tools (MCP 协议扩展点) ---
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_forum_posts",
            "description": "当用户询问关于游戏攻略、上分技巧或广场帖子时调用，以获取社区最新动态",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "搜索关键词，如 'APEX 上分'"}
                },
                "required": ["keyword"]
            }
        }
    }
]

async def execute_tool(tool_name: str, arguments: dict) -> str:
    """执行本地工具或请求外部微服务 (Tool Execution)"""
    if tool_name == "search_forum_posts":
        keyword = arguments.get("keyword", "")
        # TODO: 实际应查询 posts 表或 Elasticsearch
        return f"【系统检索结果】社区关于 '{keyword}' 的最新热帖：1. '今天APEX连败怎么调整心态' 2. '双排上分最优阵容推荐'。"
    return "工具未找到或执行失败。"

@router.post("/chat")
async def chat_with_agent(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """AI 智能体核心对话流 (支持 SSE, RAG, Tool Loop)"""
    
    # 1. 获取用户配置
    profile = (await db.execute(select(Profile).where(Profile.user_id == current_user.id))).scalars().first()
    tuning = (await db.execute(select(AgentTuning).where(AgentTuning.user_id == current_user.id))).scalars().first()
    
    system_prompt = build_system_prompt(profile, tuning)
    
    # 2. 生成当前输入的 Vector 并进行 RAG 记忆检索
    current_msg_vector = await create_embedding(request.message)
    long_term_memories = await retrieve_long_term_memory(db, current_user.id, current_msg_vector)
    
    if long_term_memories:
        memory_context = "\n".join(long_term_memories)
        system_prompt += f"\n\n【潜意识回忆】你隐约记得过去和用户的这些对话片段，适当时可作为背景参考：\n{memory_context}"

    # 3. 组装短期上下文并执行 Token 滑动窗口压缩
    recent_history = await get_short_term_memory(db, current_user.id, limit=6)
    
    raw_messages = [{"role": "system", "content": system_prompt}] + recent_history + [{"role": "user", "content": request.message}]
    messages = compress_context(raw_messages, max_tokens=8000)

    # 4. SSE 异步生成器与 Tool Loop
    async def event_generator():
        nonlocal messages
        full_ai_response = ""
        
        while True: # Tool Loop
            stream = await client.chat.completions.create(
                model="gpt-4o-mini", # 或 deepseek-chat
                messages=messages,
                tools=TOOLS,
                stream=True
            )
            
            is_tool_call = False
            tool_call_name = ""
            tool_call_args = ""
            tool_call_id = ""

            async for chunk in stream:
                delta = chunk.choices[0].delta
                
                # A. 遇到工具调用
                if delta.tool_calls:
                    is_tool_call = True
                    tc = delta.tool_calls[0]
                    if tc.id: tool_call_id = tc.id
                    if tc.function.name: tool_call_name = tc.function.name
                    if tc.function.arguments: tool_call_args += tc.function.arguments
                    continue
                
                # B. 正常的流式文本输出
                if delta.content:
                    text_chunk = delta.content
                    full_ai_response += text_chunk
                    yield f"data: {json.dumps({'content': text_chunk, 'done': False}, ensure_ascii=False)}\n\n"

            # 如果模型决定调用工具，则静默执行，中断推流并重入 Loop
            if is_tool_call:
                # 提示前端当前 AI 正在思考/使用工具
                yield f"data: {json.dumps({'tool_call': f'正在使用工具: {tool_call_name}...', 'done': False}, ensure_ascii=False)}\n\n"
                
                # 记录模型意图
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{"id": tool_call_id, "type": "function", "function": {"name": tool_call_name, "arguments": tool_call_args}}]
                })
                
                # 执行本地逻辑
                args_dict = json.loads(tool_call_args)
                tool_result = await execute_tool(tool_call_name, args_dict)
                
                # 将工具执行结果喂回给模型
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_call_name,
                    "content": tool_result
                })
                continue # 重入 Tool Loop，重新请求大模型
            
            break # 无工具调用，文本生成完毕，退出 Loop

        yield f"data: {json.dumps({'done': True})}\n\n"
        
        # 5. 生成完毕，触发异步落库与向量化任务 (注意：必须使用新的 DB Session 防止原有请求上下文关闭)
        async def background_memory_job():
            async with AsyncSessionLocal() as bg_db:
                await save_conversation_to_memory(bg_db, current_user.id, request.message, full_ai_response)
                
        background_tasks.add_task(background_memory_job)

    # 返回 Server-Sent Events 响应
    return StreamingResponse(event_generator(), media_type="text/event-stream")