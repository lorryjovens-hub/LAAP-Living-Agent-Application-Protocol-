"""PromptBuilder — 动态系统提示构建"""
from __future__ import annotations
import time, json, logging, os
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("agent_core.prompt_builder")

@dataclass
class PromptTemplate:
    name: str = ""
    content: str = ""
    variables: List[str] = field(default_factory=list)
    category: str = "general"
    priority: int = 0

class PromptBuilder:
    """动态提示构建器 — 组装system提示、注入变量、Token预算感知裁剪"""
    
    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._sections: Dict[str, str] = {}
        self._load_defaults()
    
    def _load_defaults(self):
        self.add_template(PromptTemplate("base_role", "你是LAAP智能体，一个自主的AI助手。", category="role"))
        self.add_template(PromptTemplate("chinese", "请用中文回答，简洁准确。", category="language"))
        self.add_template(PromptTemplate("tools", "你可以调用以下工具来完成任务：{tools_list}", category="capability", variables=["tools_list"]))
        self.add_template(PromptTemplate("memory", "你拥有记忆系统，可以记住用户信息和历史交互。", category="capability"))
        self.add_template(PromptTemplate("planning", "对于复杂任务，你应该先规划步骤再执行。", category="capability"))
        self.add_template(PromptTemplate("format", "回答使用Markdown格式，代码用```标注。", category="format"))
    
    def add_template(self, template: PromptTemplate):
        self._templates[template.name] = template
    
    def set_section(self, key: str, content: str):
        self._sections[key] = content
    
    def build(self, tool_descriptions: str = "", user_info: str = "",
              custom_instructions: str = "", max_tokens: int = 1000) -> str:
        """构建系统提示"""
        parts = []
        
        # 1. 角色定义
        if "base_role" in self._templates:
            parts.append(self._templates["base_role"].content)
        
        # 2. 语言指令
        if "chinese" in self._templates:
            parts.append(self._templates["chinese"].content)
        
        # 3. 自定义指令
        if custom_instructions:
            parts.append(custom_instructions)
        
        # 4. 能力声明
        if "tools" in self._templates and tool_descriptions:
            parts.append(self._templates["tools"].content.format(tools_list=tool_descriptions[:500]))
        if "memory" in self._templates:
            parts.append(self._templates["memory"].content)
        if "planning" in self._templates:
            parts.append(self._templates["planning"].content)
        
        # 5. 用户信息
        if user_info:
            parts.append(f"关于用户: {user_info[:200]}")
        
        # 6. 格式要求
        if "format" in self._templates:
            parts.append(self._templates["format"].content)
        
        # 7. 自定义章节
        for key, content in self._sections.items():
            parts.append(content)
        
        combined = "\n\n".join(parts)
        
        # Token预算裁剪
        estimated_tokens = len(combined) // 2
        if estimated_tokens > max_tokens:
            ratio = max_tokens / estimated_tokens
            cut = int(len(combined) * ratio)
            combined = combined[:cut] + "\n[以下内容因长度限制被截断]"
        
        return combined
    
    def get_stats(self) -> dict:
        return {"templates": len(self._templates), "sections": len(self._sections)}
