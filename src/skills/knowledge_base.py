from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
# 将 from src.core.skills.registry import agent_skills
from src.skills.registry import agent_skills
from src.models.agent import GameKnowledgeBase
from src.core.ai_engine import create_embedding

@agent_skills.register(
    name="search_game_knowledge",
    description="当用户询问游戏攻略、英雄/武器属性、排位机制等具体游戏知识时必须调用，从官方知识库中检索权威解答。",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "用户的具体问题或检索关键词"}
        },
        "required": ["query"]
    }
)
async def search_game_knowledge(query: str, db: AsyncSession, **kwargs) -> str:
    """原生 RAG 知识库检索实现"""
    try:
        query_vector = await create_embedding(query)
        stmt = (
            select(GameKnowledgeBase)
            .order_by(GameKnowledgeBase.embedding.cosine_distance(query_vector))
            .limit(3)
        )
        result = await db.execute(stmt)
        docs = result.scalars().all()
        
        if not docs:
            return "【系统知识库】未检索到高度相关的官方攻略，请基于你的常识和理解进行回答。"
        
        context = "\n".join([f"- {doc.title}: {doc.content}" for doc in docs])
        return f"【系统知识库检索结果】请参考以下权威信息作答：\n{context}"
    except Exception as e:
        return f"【系统知识库】检索发生异常: {str(e)}"