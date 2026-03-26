import tiktoken
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Dict, Any

from src.core.config import settings
from src.models.user import Profile
from src.models.agent import AgentTuning, AgentChatMessage, UserMemoryInsight

client = AsyncOpenAI(
    api_key=getattr(settings, "OPENAI_API_KEY", "your-api-key"),
    base_url=getattr(settings, "OPENAI_BASE_URL", "https://api.openai.com/v1")
)

tokenizer = tiktoken.get_encoding("cl100k_base")

async def create_embedding(text: str) -> List[float]:
    """将文本转化为 1536 维的向量"""
    response = await client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def build_system_prompt(profile: Profile, tuning: AgentTuning, memory_insights: List[str]) -> str:
    """动态拼装：核心人设 + 行为参数 + 长期总结记忆注入"""
    nickname = profile.nickname if profile else "玩家"
    agent_name = tuning.agent_display_name_override if tuning and tuning.agent_display_name_override else "同频搭专属智能体"
    
    # A. 基础设定 & 核心扮演
    prompt = f"你是专属于 {nickname} 的完美游戏与生活搭子。你的名字是：{agent_name}。\n"
    if tuning and tuning.custom_persona_script:
        prompt += f"【核心身份剧本】：\n{tuning.custom_persona_script}\n\n"

    # B. 行为参数与语气微调
    prompt += f"【行为与语气调优参数】\n"
    if tuning:
        prompt += f"- 情绪基调: {tuning.emotion_tone or '平和'}\n"
        prompt += f"- 幽默占比: {tuning.humor_mix or '适中'}\n"
        prompt += f"- 社交能量: {tuning.social_energy or '温和'}\n"
        prompt += f"- 文本长度: {tuning.reply_length or 'MEDIUM'} 级别。\n"
    prompt += "（必须严格口语化，像相熟的真人朋友一样交流，拒绝AI客服腔调）\n\n"

    # C. 禁忌红线
    if tuning and tuning.taboo_notes:
        prompt += f"【🔴绝对禁忌 (不惜一切代价避免触碰)】\n{tuning.taboo_notes}\n\n"

    # D. 动态深度记忆注入
    if memory_insights:
        insights_text = "\n".join([f"- {m}" for m in memory_insights])
        prompt += f"【🧠 潜意识记忆库】\n以下是你总结提取的关于用户的长期关键记忆。请在交流中自然地展现出你记得这些事：\n{insights_text}\n"

    return prompt

async def retrieve_long_term_memory(db: AsyncSession, user_id: str, query_vector: List[float], top_k: int = 3) -> List[str]:
    """原生 RAG 原始对话切片检索"""
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
    stmt = (
        select(AgentChatMessage)
        .where(AgentChatMessage.user_id == user_id)
        .order_by(desc(AgentChatMessage.created_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()[::-1]
    return [{"role": msg.role, "content": msg.content} for msg in messages]

def compress_context(messages: List[Dict[str, str]], max_tokens: int = 6000) -> List[Dict[str, str]]:
    compressed = []
    current_tokens = 0
    
    system_msg = None
    if messages and messages[0]["role"] == "system":
        system_msg = messages.pop(0)
        current_tokens += len(tokenizer.encode(system_msg["content"]))
        
    for msg in reversed(messages):
        msg_tokens = len(tokenizer.encode(str(msg.get("content", ""))))
        if current_tokens + msg_tokens > max_tokens:
            break
        compressed.insert(0, msg)
        current_tokens += msg_tokens
        
    if system_msg:
        compressed.insert(0, system_msg)
        
    return compressed

async def save_conversation_to_memory(db: AsyncSession, user_id: str, user_msg: str, ai_msg: str):
    """原始对话切片双向落库固化"""
    try:
        memory_slice = f"用户说：{user_msg} \n你回答：{ai_msg}"
        slice_vector = await create_embedding(memory_slice)
        
        user_record = AgentChatMessage(user_id=user_id, role="user", content=user_msg, embedding=slice_vector)
        ai_record = AgentChatMessage(user_id=user_id, role="assistant", content=ai_msg, embedding=slice_vector)
        
        db.add_all([user_record, ai_record])
        await db.commit()
    except Exception as e:
        print(f"Memory Solidification Failed: {e}")

async def extract_and_store_memory(db: AsyncSession, user_id: str, user_msg: str, ai_msg: str):
    """后台任务：AI 提取用户深层特征/事实并向量化写入 UserMemoryInsight"""
    extraction_prompt = f"""
    请深度分析以下用户与AI的最新对话。提取关于该用户的**高价值长期记忆**（例如：常玩游戏、特定操作习惯、情绪雷区、作息规律、现实身份信息等）。
    如果没有提取出长期值得记住的新事实，请严格、仅回复 "NONE"。
    如果提取成功，请用一句简明扼要的陈述句进行总结归纳（第一人称指代AI，第三人称指代用户）。
    
    用户: {user_msg}
    AI: {ai_msg}
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini", # 高性价比模型专门负责数据清洗
            messages=[{"role": "system", "content": extraction_prompt}],
            max_tokens=100,
            temperature=0.2
        )
        insight = response.choices[0].message.content.strip()
        
        if insight != "NONE" and len(insight) > 2:
            insight_vector = await create_embedding(insight)
            record = UserMemoryInsight(
                user_id=user_id, 
                insight_text=insight, 
                embedding=insight_vector
            )
            db.add(record)
            await db.commit()
    except Exception as e:
        print(f"Memory extraction failed: {e}")