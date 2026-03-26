import json
from typing import Callable, Dict, Any, List

class SkillRegistry:
    """Skill 驱动的 Tool/MCP 动态注册表"""
    def __init__(self):
        self._skills: Dict[str, dict] = {}
        self._handlers: Dict[str, Callable] = {}

    def register(self, name: str, description: str, parameters: dict):
        """装饰器：注册一个新的 Agent 技能 (Tool)"""
        def decorator(func: Callable):
            self._skills[name] = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": parameters
                }
            }
            self._handlers[name] = func
            return func
        return decorator

    def get_tools_schema(self) -> List[dict]:
        """获取注入给 LLM 的标准 Schema 列表"""
        return list(self._skills.values())

    async def execute_skill(self, name: str, args_json: str, **kwargs) -> str:
        """执行对应的技能处理器"""
        if name not in self._handlers:
            return f"Error: Skill '{name}' not found."
        try:
            args = json.loads(args_json) if args_json else {}
            handler = self._handlers[name]
            # 执行工具，动态透传环境上下文 (如 db session, user_id)
            return await handler(**args, **kwargs)
        except Exception as e:
            return f"Error executing skill '{name}': {str(e)}"

# 全局单例注册表
agent_skills = SkillRegistry()