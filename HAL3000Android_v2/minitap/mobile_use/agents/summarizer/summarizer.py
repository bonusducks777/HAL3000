from langchain_core.messages import (
    HumanMessage,
    RemoveMessage,
    ToolMessage,
)

from minitap.mobile_use.constants import MAX_MESSAGES_IN_HISTORY
from minitap.mobile_use.context import MobileUseContext
from minitap.mobile_use.graph.state import State
from minitap.mobile_use.agents.planner.utils import get_current_subgoal
from minitap.mobile_use.utils.logger import get_logger

logger = get_logger(__name__)


class SummarizerNode:
    def __init__(self, ctx: MobileUseContext):
        self.ctx = ctx

    def __call__(self, state: State):
        # HAL3000Android: Track execution depth
        new_depth = state.execution_depth + 1
        logger.info(f"🔢 Summarizer Agent (#{new_depth})")
        
        # HAL3000Android: After successful tool execution, mark current subgoal for examination
        current_subgoal = get_current_subgoal(state.subgoal_plan)
        update_dict = {}
        
        if current_subgoal and current_subgoal.id not in state.complete_subgoals_by_ids:
            logger.info(f"🎯 Marking subgoal for examination: {current_subgoal.id}")
            update_dict["complete_subgoals_by_ids"] = state.complete_subgoals_by_ids + [current_subgoal.id]
        
        # Always update execution depth
        update_dict["execution_depth"] = new_depth
        
        if len(state.messages) <= MAX_MESSAGES_IN_HISTORY:
            return state.sanitize_update(
                ctx=self.ctx,
                update=update_dict,
                agent="summarizer",
            ) if update_dict else {}

        nb_removal_candidates = len(state.messages) - MAX_MESSAGES_IN_HISTORY

        remove_messages = []
        start_removal = False

        for msg in reversed(state.messages[:nb_removal_candidates]):
            if isinstance(msg, ToolMessage | HumanMessage):
                start_removal = True
            if start_removal and msg.id:
                remove_messages.append(RemoveMessage(id=msg.id))
            
            update_dict["messages"] = remove_messages
            return state.sanitize_update(
                ctx=self.ctx,
                update=update_dict,
                agent="summarizer",
            )
