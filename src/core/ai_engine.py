import tiktoken
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Dict, Any

from src.core.config import settings
from src.models.user import Profile
from src.models.agent import AgentTuning, AgentChatMessage

# 初始化 OpenAI 异步客户端 (兼容 DeepSeek 等原生 OpenAI 协议的模型)
# 请在 .env 中配置 OPENAI_API_KEY，或修改 BASE_URL 指向 DeepSeek
client = AsyncOpenAI(
    api_key=getattr(settings, "OPENAI_API_KEY", "your-api-key"),
    base_url=getattr(settings, "OPENAI_BASE_URL", "https://api.openai.com/v1")
)

# 默认使用 cl100k_base 编码 (GPT-4 / DeepSeek 通用)
tokenizer = tiktoken.get_encoding("cl100k_base")

async def create_embedding(text: str) -> List[float]:
    """将文本转化为 1536 维的向量"""
    response = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small" # 或其他 embedding 模型
    )
    return response.data[0].embedding

def build_system_prompt(profile: Profile, tuning: AgentTuning) -> str:
    """基于 Android 端 AgentTuning 动态组装 System Prompt"""
    nickname = profile.nickname if profile else "玩家"
    agent_name = tuning.agent_display_name_override if tuning and tuning.agent_display_name_override else "同频搭智能体"
    
    prompt = f"你是一个专属于 {nickname} 的游戏与生活搭子。你的名字是：{agent_name}。\n"
    
    if tuning:
        prompt += f"""
【核心人设设定】
- 语气与情绪基调：{tuning.voice_mood or '自然'}、{tuning.emotion_tone or '平和'}
- 幽默程度：{tuning.humor_mix or '适中'}
- 社交能量：{tuning.social_energy or '温和'}
- 互动主动性：{tuning.initiative_level or '回应型'}

【专属自定义规则】
- 用户自定义剧本/总则：{tuning.custom_persona_script or '无'}
- 额外指示：{tuning.extra_instructions or '无'}

【绝对禁忌 (红线，绝不可触碰)】
{tuning.taboo_notes or '无'}

【对话策略】
1. 你的回复长度应保持在 {tuning.reply_length or 'MEDIUM'} 级别。
2. 必须以自然、口语化、像真人朋友一样的方式回复，绝对不要像一个冷冰冰的AI客服。
"""
    return prompt

async def retrieve_long_term_memory(db: AsyncSession, user_id: str, query_vector: List[float], top_k: int = 3) -> List[str]:
    """RAG: 长期语义记忆检索 (利用 pgvector 的 cosine_distance)"""
    stmt = (
        select(AgentChatMessage)
        .where(AgentChatMessage.user_id == user_id)
        .order_by(AgentChatMessage.embedding.cosine_distance(query_vector))
        .limit(top_k)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()
    return [msg.content for msg in messages]

async def get_short_term_memory(db: AsyncSession, user_id: str, limit: int = 6) -> List[Dict[str, str]]:
    """获取最近的短期记忆 (滑动窗口)"""
    stmt = (
        select(AgentChatMessage)
        .where(AgentChatMessage.user_id == user_id)
        .order_by(desc(AgentChatMessage.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    # 数据库是倒序取出的，需要反转恢复时间顺序
    messages = result.scalars().all()[::-1]
    return [{"role": msg.role, "content": msg.content} for msg in messages]

def compress_context(messages: List[Dict[str, str]], max_tokens: int = 6000) -> List[Dict[str, str]]:
    """滑动窗口 Token 截断：确保不超出模型上下文限制"""
    compressed = []
    current_tokens = 0
    
    # 始终保留 System Prompt (通常是第一条)
    system_msg = None
    if messages and messages[0]["role"] == "system":
        system_msg = messages.pop(0)
        current_tokens += len(tokenizer.encode(system_msg["content"]))
        
    # 从最新的消息开始往前推算，保留尽可能多的短期历史
    for msg in reversed(messages):
        msg_tokens = len(tokenizer.encode(str(msg.get("content", ""))))
        if current_tokens + msg_tokens > max_tokens:
            break # 超出限制，丢弃更早的历史
        compressed.insert(0, msg)
        current_tokens += msg_tokens
        
    if system_msg:
        compressed.insert(0, system_msg)
        
    return compressed

async def save_conversation_to_memory(db: AsyncSession, user_id: str, user_msg: str, ai_msg: str):
    """记忆固化：后台异步将对话双向存入 DB 并向量化"""
    try:
        # 为合并的对话切片生成 Embedding (降低数据库检索的碎片度)
        memory_slice = f"用户说：{user_msg} \n你回答：{ai_msg}"
        slice_vector = await create_embedding(memory_slice)
        
        user_record = AgentChatMessage(user_id=user_id, role="user", content=user_msg, embedding=slice_vector)
        ai_record = AgentChatMessage(user_id=user_id, role="assistant", content=ai_msg, embedding=slice_vector)
        
        db.add_all([user_record, ai_record])
        await db.commit()
    except Exception as e:
        print(f"Memory Solidification Failed: {e}")