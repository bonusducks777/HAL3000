"""
Knowledge Base Integration for HAL3000Android
Provides context injection for all AI calls
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)


def load_knowledge_base() -> Optional[Dict[str, Any]]:
    """Load knowledge base from knowledgebase.json"""
    try:
        # Look for knowledgebase.json in project root
        root_dir = Path(__file__).parent.parent.parent.parent
        kb_file = root_dir / "knowledgebase.json"
        
        if kb_file.exists():
            with open(kb_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.debug("No knowledgebase.json found")
            return None
    except Exception as e:
        logger.error(f"Failed to load knowledge base: {e}")
        return None


def format_knowledge_context() -> str:
    """Format knowledge base content for AI context injection"""
    kb = load_knowledge_base()
    if not kb:
        return ""
    
    context_parts = []
    
    # Add system context
    if "system_context" in kb:
        context_parts.append(f"System: {kb['system_context']}")
    
    # Add user context
    if "user_context" in kb and isinstance(kb["user_context"], list):
        user_context = " | ".join(kb["user_context"])
        context_parts.append(f"User Context: {user_context}")
    
    # Add capabilities
    if "capabilities" in kb and isinstance(kb["capabilities"], list):
        capabilities = " | ".join(kb["capabilities"])
        context_parts.append(f"Capabilities: {capabilities}")
    
    # Add best practices
    if "best_practices" in kb and isinstance(kb["best_practices"], list):
        practices = " | ".join(kb["best_practices"])
        context_parts.append(f"Best Practices: {practices}")
    
    return " || ".join(context_parts)


def enhance_system_message(original_message: str) -> str:
    """Enhance system message with knowledge base context"""
    kb_context = format_knowledge_context()
    if not kb_context:
        return original_message
    
    # Add knowledge base context to the end of the system message
    enhanced = f"{original_message}\n\n## HAL3000Android Context\n{kb_context}"
    logger.debug("Enhanced system message with knowledge base context")
    return enhanced


def enhance_agent_prompt(agent_name: str, original_prompt: str) -> str:
    """Enhance agent-specific prompt with knowledge base context"""
    kb = load_knowledge_base()
    if not kb:
        return original_prompt
    
    # Add agent-specific context if available
    agent_context = ""
    if f"{agent_name}_context" in kb:
        agent_context = f"\n\n## {agent_name.title()} Specific Context\n{kb[f'{agent_name}_context']}"
    
    general_context = format_knowledge_context()
    if general_context:
        general_context = f"\n\n## HAL3000Android Context\n{general_context}"
    
    return f"{original_prompt}{agent_context}{general_context}"