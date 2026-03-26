from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional

class AgentTuningBase(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
    
    # 前端对应 agentChatUnlocked，后端对应 is_unlocked
    is_unlocked: bool = Field(default=False, alias="agentChatUnlocked")
    
    intensity: int = Field(default=50)
    reply_length: str = Field(default="MEDIUM")
    focus_scenario: Optional[str] = None
    emotion_tone: Optional[str] = None
    humor_mix: Optional[str] = None
    social_energy: Optional[str] = None
    wit_style: Optional[str] = None
    stance_mode: Optional[str] = None
    initiative_level: Optional[str] = None
    address_style: Optional[str] = None
    avatar_style: Optional[str] = None
    avatar_frame: Optional[str] = None
    bubble_style: Optional[str] = None
    voice_mood: Optional[str] = None
    agent_display_name_override: Optional[str] = None
    extra_instructions: Optional[str] = None
    taboo_notes: Optional[str] = None
    custom_persona_script: Optional[str] = None
    custom_phrase_1: Optional[str] = None
    custom_phrase_2: Optional[str] = None
    custom_phrase_3: Optional[str] = None

class AgentTuningUpdate(AgentTuningBase):
    pass