import uuid
from pathlib import Path

from jinja2 import Template
from langchain_core.messages import HumanMessage, SystemMessage

from minitap.mobile_use.agents.planner.types import PlannerOutput, Subgoal, SubgoalStatus
from minitap.mobile_use.agents.planner.utils import one_of_them_is_failure
from minitap.mobile_use.context import MobileUseContext
from minitap.mobile_use.graph.state import State
from minitap.mobile_use.services.llm import get_llm
from minitap.mobile_use.tools.index import EXECUTOR_WRAPPERS_TOOLS, format_tools_list
from minitap.mobile_use.utils.decorators import wrap_with_callbacks
from minitap.mobile_use.utils.logger import get_logger

logger = get_logger(__name__)


class PlannerNode:
    def __init__(self, ctx: MobileUseContext):
        self.ctx = ctx

    @wrap_with_callbacks(
        before=lambda: logger.info("Starting Planner Agent..."),
        on_success=lambda _: logger.success("Planner Agent"),
        on_failure=lambda _: logger.error("Planner Agent"),
    )
    async def __call__(self, state: State):
        # HAL3000Android: Track execution depth
        new_depth = state.execution_depth + 1
        logger.info(f"🔢 Planner Agent (#{new_depth})")
        
        needs_replan = one_of_them_is_failure(state.subgoal_plan)
        
        # HAL3000Android: Don't replace existing plan unless it needs replanning
        if state.subgoal_plan and not needs_replan:
            logger.info("📜 Existing plan is still valid, skipping planner")
            return state.sanitize_update(
                ctx=self.ctx,
                update={"execution_depth": new_depth},
                agent="planner",
            )

        system_message = Template(
            Path(__file__).parent.joinpath("planner.md").read_text(encoding="utf-8")
        ).render(
            platform=self.ctx.device.mobile_platform.value,
            executor_tools_list=format_tools_list(ctx=self.ctx, wrappers=EXECUTOR_WRAPPERS_TOOLS),
        )
        
        # HAL3000Android: Enhance with knowledge base context
        from minitap.mobile_use.utils.knowledge_base import enhance_agent_prompt
        system_message = enhance_agent_prompt("planner", system_message)
        human_message = Template(
            Path(__file__).parent.joinpath("human.md").read_text(encoding="utf-8")
        ).render(
            action="replan" if needs_replan else "plan",
            initial_goal=state.initial_goal,
            previous_plan="\n".join(str(s) for s in state.subgoal_plan),
            agent_thoughts="\n".join(state.agents_thoughts),
            screen_analysis=state.screen_analysis,
        )
        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=human_message),
        ]

        llm = get_llm(ctx=self.ctx, name="planner")
        if hasattr(llm, "is_cerebras"):
            # Cerebras
            # Add tool information to system message
            enhanced_system_message = system_message + """

CRITICAL: You must respond in this EXACT JSON format:
{
  "subgoals": [
    {
      "id": null,
      "description": "First step description"
    },
    {
      "id": null, 
      "description": "Second step description"
    }
  ]
}

Do NOT return just an array. Always wrap in an object with "subgoals" key.
"""
            
            cerebras_msgs = []
            for m in messages:
                if hasattr(m, "content"):
                    role = "system" if m.__class__.__name__ == "SystemMessage" else "user"
                    content = m.content if m != messages[0] else enhanced_system_message
                    if role == "system" and "JSON" not in content:
                        content += "\nRespond ONLY in valid JSON format."
                    cerebras_msgs.append({"role": role, "content": content})
                else:
                    cerebras_msgs.append(m)
            response_obj = llm.generate(cerebras_msgs, response_format={"type": "json_object"})
            response = PlannerOutput.model_validate_json(response_obj.content)
        else:
            llm = llm.with_structured_output(PlannerOutput)
            response: PlannerOutput = await llm.ainvoke(messages)  # type: ignore

        subgoals_plan = [
            Subgoal(
                id=subgoal.id or str(uuid.uuid4()),
                description=subgoal.description,
                status=SubgoalStatus.NOT_STARTED,
                completion_reason=None,
            )
            for subgoal in response.subgoals
        ]
        logger.info("📜 Generated plan:")
        logger.info("\n".join(str(s) for s in subgoals_plan))

        return state.sanitize_update(
            ctx=self.ctx,
            update={
                "subgoal_plan": subgoals_plan,
                "execution_depth": new_depth,
            },
            agent="planner",
        )
