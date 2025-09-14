from pathlib import Path

from jinja2 import Template
from langchain_core.messages import HumanMessage, SystemMessage
from minitap.mobile_use.context import MobileUseContext
from minitap.mobile_use.services.llm import get_llm
from pydantic import BaseModel, Field


class HopperOutput(BaseModel):
    step: str = Field(
        description=(
            "The step that has been done, must be a valid one following the "
            "current steps and the current goal to achieve."
        )
    )
    output: str = Field(description="The interesting data extracted from the input data.")


async def hopper(
    ctx: MobileUseContext,
    request: str,
    data: str,
) -> HopperOutput:
    print("Starting Hopper Agent", flush=True)
    system_message = Template(
        Path(__file__).parent.joinpath("hopper.md").read_text(encoding="utf-8")
    ).render()
    
    # HAL3000Android: Enhance with knowledge base context
    from minitap.mobile_use.utils.knowledge_base import enhance_agent_prompt
    system_message = enhance_agent_prompt("hopper", system_message)
    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=f"{request}\nHere is the data you must dig:\n{data}"),
    ]

    llm = get_llm(ctx=ctx, name="hopper", is_utils=True, temperature=0)
    if hasattr(llm, "is_cerebras"):
        # Cerebras
        cerebras_msgs = []
        for m in messages:
            if hasattr(m, "content"):
                role = "system" if m.__class__.__name__ == "SystemMessage" else "user"
                content = m.content
                if role == "system" and "JSON" not in content:
                    content += "\nRespond ONLY in valid JSON format."
                cerebras_msgs.append({"role": role, "content": content})
            else:
                cerebras_msgs.append(m)
        response_obj = llm.generate(cerebras_msgs, response_format={"type": "json_object"})
        response = HopperOutput.model_validate_json(response_obj.content)
    else:
        structured_llm = llm.with_structured_output(HopperOutput)
        response: HopperOutput = await structured_llm.ainvoke(messages)  # type: ignore
    return HopperOutput(
        step=response.step,
        output=response.output,
    )
