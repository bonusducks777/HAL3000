from minitap.mobile_use.agents.executor.utils import is_last_tool_message_take_screenshot
from minitap.mobile_use.context import MobileUseContext
from minitap.mobile_use.controllers.mobile_command_controller import get_screen_data
from minitap.mobile_use.controllers.platform_specific_commands_controller import (
    get_device_date,
    get_focused_app_info,
)
from minitap.mobile_use.graph.state import State
from minitap.mobile_use.utils.decorators import wrap_with_callbacks
from minitap.mobile_use.utils.logger import get_logger
from minitap.mobile_use.utils.conversations import is_tool_message
from minitap.mobile_use.services.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage

logger = get_logger(__name__)

# UI-changing actions that should trigger automatic screenshots
UI_CHANGING_ACTIONS = {"swipe", "tap", "key", "type", "scroll"}


def should_capture_screenshot(messages: list) -> bool:
    """Check if we should capture a screenshot based on recent actions"""
    # Always capture if explicitly requested
    if is_last_tool_message_take_screenshot(messages):
        return True
    
    # Also capture after UI-changing actions
    if not messages:
        return False
    
    for msg in messages[::-1]:
        if is_tool_message(msg):
            # Capture screenshot after UI-changing actions
            return msg.name in UI_CHANGING_ACTIONS
    
    return False


class ContextorNode:
    def __init__(self, ctx: MobileUseContext):
        self.ctx = ctx

    @wrap_with_callbacks(
        before=lambda: logger.info("Starting Contextor Agent"),
        on_success=lambda _: logger.success("Contextor Agent"),
        on_failure=lambda _: logger.error("Contextor Agent"),
    )
    async def __call__(self, state: State):
        # HAL3000Android: Track execution depth
        new_depth = state.execution_depth + 1
        logger.info(f"🔢 Contextor Agent (#{new_depth})")
        
        device_data = get_screen_data(self.ctx.screen_api_client)
        focused_app_info = get_focused_app_info(self.ctx)
        device_date = get_device_date(self.ctx)

        should_add_screenshot_context = should_capture_screenshot(
            list(state.executor_messages)
        )

        # For initial planning (no subgoal plan yet), always capture screenshot and provide vision analysis
        is_initial_planning = not state.subgoal_plan
        if is_initial_planning:
            should_add_screenshot_context = True
            
            # Use vision model to analyze current screen state
            llm = get_llm(ctx=self.ctx, name="contextor", temperature=0)
            
            system_message = """You are a screen analyzer for mobile automation. Analyze the current screen and provide a brief, clear description of:

1. What app/screen is currently visible
2. Key UI elements that are present 
3. The current state (locked, home screen, in an app, etc.)

Keep your response concise and focused on what's visible that would help plan automation steps."""

            messages = [
                SystemMessage(content=system_message),
                HumanMessage(content=[
                    {"type": "text", "text": f"Analyze this {self.ctx.device.mobile_platform.value} screen:"},
                    {"type": "image_url", "image_url": {"url": device_data.base64}}
                ])
            ]
            
            try:
                screen_analysis = await llm.ainvoke(messages)
                logger.info(f"📸 Screen Analysis: {screen_analysis.content}")
            except Exception as e:
                logger.error(f"Vision analysis failed: {e}")
                screen_analysis = None
        else:
            screen_analysis = None

        return state.sanitize_update(
            ctx=self.ctx,
            update={
                "latest_screenshot_base64": device_data.base64
                if should_add_screenshot_context
                else None,
                "latest_ui_hierarchy": device_data.elements,
                "focused_app_info": focused_app_info,
                "screen_size": (device_data.width, device_data.height),
                "device_date": device_date,
                "screen_analysis": screen_analysis.content if screen_analysis else state.screen_analysis,
                "execution_depth": new_depth,
            },
            agent="contextor",
        )
