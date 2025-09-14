from pydantic import BaseModel, Field


class CortexOutput(BaseModel):
    decisions: str = Field(default="{}", description="The decisions to be made. A stringified JSON object. Use empty dict '{}' when completing subgoals.")
    agent_thought: str = Field(..., description="The agent's thought")
    complete_subgoals_by_ids: list[str] | None = Field(
        [], description="List of subgoal IDs to complete"
    )
