
import logging
from collections.abc import Awaitable, Callable
from typing import Literal, TypeVar, overload, List, Dict, Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# Cerebras SDK
try:
    from cerebras.cloud.sdk import Cerebras
except ImportError:
    Cerebras = None

from minitap.mobile_use.config import (
    AgentNode,
    AgentNodeWithFallback,
    LLMUtilsNode,
    LLMWithFallback,
    settings,
)
from minitap.mobile_use.context import MobileUseContext

logger = logging.getLogger(__name__)

class CerebrasLLMWrap:
    def __init__(self, api_key: str, model: str):
        self.client = Cerebras(api_key=api_key)
        self.model = model
        self.is_cerebras = True  # Unique identifier for Cerebras
    
    def generate(self, messages: List[Dict[str, str]], response_format: Dict[str, str] = None):
        """Generate response using Cerebras API - synchronous method to match agent expectations"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }
        
        if response_format:
            kwargs["response_format"] = response_format
            
        response = self.client.chat.completions.create(**kwargs)
        
        # Create a simple object that mimics LangChain's response structure
        class CerebrasResponse:
            def __init__(self, content: str):
                self.content = content
        
        # Extract content from Cerebras response and wrap it
        content = response.choices[0].message.content
        return CerebrasResponse(content)

def get_cerebras_llm(
    model_name: str = "qwen-3-235b-a22b-instruct-2507",
    temperature: float = 0.7,
    max_completion_tokens: int = 20000,
) -> Any:
    assert Cerebras is not None, "Cerebras SDK not installed!"
    assert settings.CEREBRAS_API_KEY is not None
    print(f"[DEBUG] CEREBRAS_API_KEY: {settings.CEREBRAS_API_KEY}")
    api_key_str = settings.CEREBRAS_API_KEY.get_secret_value() if hasattr(settings.CEREBRAS_API_KEY, "get_secret_value") else str(settings.CEREBRAS_API_KEY)
    return CerebrasLLMWrap(api_key_str, model_name)


def get_google_llm(
    model_name: str = "gemini-2.5-pro",
    temperature: float = 0.7,
) -> ChatGoogleGenerativeAI:
    assert settings.GOOGLE_API_KEY is not None
    client = ChatGoogleGenerativeAI(
        model=model_name,
        max_tokens=None,
        temperature=temperature,
        api_key=settings.GOOGLE_API_KEY,
        max_retries=2,
    )
    return client


def get_vertex_llm(
    model_name: str = "gemini-2.5-pro",
    temperature: float = 0.7,
) -> ChatVertexAI:
    client = ChatVertexAI(
        model_name=model_name,
        max_tokens=None,
        temperature=temperature,
        max_retries=2,
    )
    return client


def get_anthropic_llm(
    model_name: str = "claude-3-5-sonnet-20241022",
    temperature: float = 0.7,
) -> ChatAnthropic:
    assert settings.ANTHROPIC_API_KEY is not None
    client = ChatAnthropic(
        model=model_name,
        api_key=settings.ANTHROPIC_API_KEY,
        temperature=temperature,
    )
    return client


def get_openai_llm(
    model_name: str = "o3",
    temperature: float = 1,
) -> ChatOpenAI:
    assert settings.OPENAI_API_KEY is not None
    client = ChatOpenAI(
        model=model_name,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=temperature,
    )
    return client


def get_openrouter_llm(model_name: str, temperature: float = 1):
    assert settings.OPEN_ROUTER_API_KEY is not None
    client = ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=settings.OPEN_ROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )
    return client


def get_grok_llm(model_name: str, temperature: float = 1) -> ChatOpenAI:
    assert settings.XAI_API_KEY is not None
    client = ChatOpenAI(
        model=model_name,
        api_key=settings.XAI_API_KEY,
        temperature=temperature,
        base_url="https://api.x.ai/v1",
    )
    return client


@overload
def get_llm(
    ctx: MobileUseContext,
    name: AgentNodeWithFallback,
    *,
    use_fallback: bool = False,
    temperature: float = 1,
) -> BaseChatModel: ...


@overload
def get_llm(
    ctx: MobileUseContext,
    name: AgentNode,
    *,
    temperature: float = 1,
) -> BaseChatModel: ...


@overload
def get_llm(
    ctx: MobileUseContext,
    name: LLMUtilsNode,
    *,
    is_utils: Literal[True],
    temperature: float = 1,
) -> BaseChatModel: ...


def get_llm(
    ctx: MobileUseContext,
    name: AgentNode | LLMUtilsNode | AgentNodeWithFallback,
    is_utils: bool = False,
    use_fallback: bool = False,
    temperature: float = 1,
) -> BaseChatModel:
    llm = (
        ctx.llm_config.get_utils(name)  # type: ignore
        if is_utils
        else ctx.llm_config.get_agent(name)  # type: ignore
    )
    if use_fallback:
        if isinstance(llm, LLMWithFallback):
            llm = llm.fallback
        else:
            raise ValueError("LLM has no fallback!")
    if llm.provider == "openai":
        return get_openai_llm(llm.model, temperature)
    elif llm.provider == "google":
        return get_google_llm(llm.model, temperature)
    elif llm.provider == "vertexai":
        return get_vertex_llm(llm.model, temperature)
    elif llm.provider == "openrouter":
        return get_openrouter_llm(llm.model, temperature)
    elif llm.provider == "xai":
        return get_grok_llm(llm.model, temperature)
    elif llm.provider == "cerebras":
        return get_cerebras_llm(llm.model, temperature)
    elif llm.provider == "anthropic":
        return get_anthropic_llm(llm.model, temperature)
    else:
        raise ValueError(f"Unsupported provider: {llm.provider}")


T = TypeVar("T")


async def with_fallback(
    main_call: Callable[[], Awaitable[T]],
    fallback_call: Callable[[], Awaitable[T]],
    none_should_fallback: bool = True,
) -> T:
    try:
        result = await main_call()
        if result is None and none_should_fallback:
            logger.warning("Main LLM inference returned None. Falling back...")
            return await fallback_call()
        return result
    except Exception as e:
        logger.warning(f"❗ Main LLM inference failed: {e}. Falling back...")
        return await fallback_call()
