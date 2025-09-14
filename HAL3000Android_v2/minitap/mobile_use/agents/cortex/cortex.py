import json
from pathlib import Path

from jinja2 import Template
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph.message import REMOVE_ALL_MESSAGES

from minitap.mobile_use.agents.cortex.types import CortexOutput
from minitap.mobile_use.agents.planner.utils import get_current_subgoal
from minitap.mobile_use.constants import EXECUTOR_MESSAGES_KEY
from minitap.mobile_use.context import MobileUseContext
from minitap.mobile_use.graph.state import State
from minitap.mobile_use.services.llm import get_llm, with_fallback
from minitap.mobile_use.tools.index import EXECUTOR_WRAPPERS_TOOLS, format_tools_list
from minitap.mobile_use.utils.conversations import get_screenshot_message_for_llm
from minitap.mobile_use.utils.decorators import wrap_with_callbacks
from minitap.mobile_use.utils.logger import get_logger

logger = get_logger(__name__)


class CortexNode:
    def __init__(self, ctx: MobileUseContext):
        self.ctx = ctx

    @wrap_with_callbacks(
        before=lambda: logger.info("Starting Cortex Agent..."),
        on_success=lambda _: logger.success("Cortex Agent"),
        on_failure=lambda _: logger.error("Cortex Agent"),
    )
    async def __call__(self, state: State):
        # HAL3000Android: Track execution depth
        new_depth = state.execution_depth + 1
        logger.info(f"🔢 Cortex Agent (#{new_depth})")
        
        executor_feedback = get_executor_agent_feedback(state)

        system_message = Template(
            Path(__file__).parent.joinpath("cortex.md").read_text(encoding="utf-8")
        ).render(
            platform=self.ctx.device.mobile_platform.value,
            initial_goal=state.initial_goal,
            subgoal_plan=state.subgoal_plan,
            current_subgoal=get_current_subgoal(state.subgoal_plan),
            executor_feedback=executor_feedback,
            executor_tools_list=format_tools_list(ctx=self.ctx, wrappers=EXECUTOR_WRAPPERS_TOOLS),
        )
        
        # HAL3000Android: Enhance with knowledge base context
        from minitap.mobile_use.utils.knowledge_base import enhance_agent_prompt
        system_message = enhance_agent_prompt("cortex", system_message)
        messages = [
            SystemMessage(content=system_message),
            HumanMessage(
                content="Here are my device info:\n"
                + self.ctx.device.to_str()
                + f"Device date: {state.device_date}\n"
                if state.device_date
                else "" + f"Focused app info: {state.focused_app_info}\n"
                if state.focused_app_info
                else ""
            ),
        ]
        for thought in state.agents_thoughts:
            messages.append(AIMessage(content=thought))

        if state.latest_screenshot_base64:
            messages.append(get_screenshot_message_for_llm(state.latest_screenshot_base64))
            logger.info("Added screenshot to context")

        if state.latest_ui_hierarchy:
            ui_hierarchy_dict: list[dict] = state.latest_ui_hierarchy
            ui_hierarchy_str = json.dumps(ui_hierarchy_dict, indent=2, ensure_ascii=False)
            messages.append(HumanMessage(content="Here is the UI hierarchy:\n" + ui_hierarchy_str))

        llm = get_llm(ctx=self.ctx, name="cortex", temperature=1)
        llm_fallback = get_llm(ctx=self.ctx, name="cortex", use_fallback=True, temperature=1)
        
        if hasattr(llm, "is_cerebras"):
            # Cerebras
            cerebras_msgs = []
            for m in messages:
                if hasattr(m, "content"):
                    if m.__class__.__name__ == "SystemMessage":
                        role = "system"
                    elif m.__class__.__name__ == "AIMessage":
                        role = "assistant"
                    else:
                        role = "user"
                    content = m.content
                    if role == "system" and "JSON" not in content:
                        content += "\nRespond ONLY in valid JSON format."
                    cerebras_msgs.append({"role": role, "content": content})
                elif isinstance(m, str):
                    cerebras_msgs.append({"role": "user", "content": m})
                else:
                    cerebras_msgs.append(m)
            response_obj = llm.generate(cerebras_msgs, response_format={"type": "json_object"})
            print(f"[DEBUG] Cerebras response type: {type(response_obj)}")
            print(f"[DEBUG] Cerebras response dir: {dir(response_obj)}")
            print(f"[DEBUG] Cerebras response: {response_obj}")
            if hasattr(response_obj, 'choices'):
                print(f"[DEBUG] Choices length: {len(response_obj.choices)}")
                print(f"[DEBUG] Choice 0: {response_obj.choices[0]}")
                print(f"[DEBUG] Choice 0 type: {type(response_obj.choices[0])}")
                if hasattr(response_obj.choices[0], 'message'):
                    print(f"[DEBUG] Message: {response_obj.choices[0].message}")
                    print(f"[DEBUG] Message type: {type(response_obj.choices[0].message)}")
                    if hasattr(response_obj.choices[0].message, 'content'):
                        print(f"[DEBUG] Message content: {response_obj.content}")
            response = CortexOutput.model_validate_json(response_obj.content)
        else:
            llm = llm.with_structured_output(CortexOutput)
            llm_fallback = llm_fallback.with_structured_output(CortexOutput)
            response: CortexOutput = await with_fallback(
                main_call=lambda: llm.ainvoke(messages),
                fallback_call=lambda: llm_fallback.ainvoke(messages),
            )  # type: ignore

        is_subgoal_completed = (
            response.complete_subgoals_by_ids is not None
            and len(response.complete_subgoals_by_ids) > 0
            and (len(response.decisions) == 0 or response.decisions in ["{}", "[]", "null", ""])
        )
        if not is_subgoal_completed:
            response.complete_subgoals_by_ids = []

        return state.sanitize_update(
            ctx=self.ctx,
            update={
                "agents_thoughts": [response.agent_thought],
                "structured_decisions": response.decisions if not is_subgoal_completed else None,
                "complete_subgoals_by_ids": response.complete_subgoals_by_ids or [],
                "latest_screenshot_base64": None,
                "latest_ui_hierarchy": None,
                "focused_app_info": None,
                "device_date": None,
                # Executor related fields
                EXECUTOR_MESSAGES_KEY: [RemoveMessage(id=REMOVE_ALL_MESSAGES)],
                "cortex_last_thought": response.agent_thought,
                "execution_depth": new_depth,
            },
            agent="cortex",
        )


def get_executor_agent_feedback(state: State) -> str:
    if state.structured_decisions is None:
        return "None."
    executor_tool_messages = [m for m in state.executor_messages if isinstance(m, ToolMessage)]
    return (
        f"Latest UI decisions:\n{state.structured_decisions}"
        + "\n\n"
        + f"Executor feedback:\n{executor_tool_messages}"
    )
