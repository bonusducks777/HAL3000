from pathlib import Path

from jinja2 import Template
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai.chat_models import ChatVertexAI

from minitap.mobile_use.constants import EXECUTOR_MESSAGES_KEY
from minitap.mobile_use.context import MobileUseContext
from minitap.mobile_use.graph.state import State
from minitap.mobile_use.services.llm import get_llm
from minitap.mobile_use.tools.index import EXECUTOR_WRAPPERS_TOOLS, get_tools_from_wrappers
from minitap.mobile_use.utils.decorators import wrap_with_callbacks
from minitap.mobile_use.utils.logger import get_logger

logger = get_logger(__name__)


class ExecutorNode:
    def __init__(self, ctx: MobileUseContext):
        self.ctx = ctx

    @wrap_with_callbacks(
        before=lambda: logger.info("Starting Executor Agent..."),
        on_success=lambda _: logger.success("Executor Agent"),
        on_failure=lambda _: logger.error("Executor Agent"),
    )
    async def __call__(self, state: State):
        # HAL3000Android: Track execution depth
        new_depth = state.execution_depth + 1
        logger.info(f"🔢 Executor Agent (#{new_depth})")
        
        structured_decisions = state.structured_decisions
        if not structured_decisions:
            logger.warning("No structured decisions found.")
            return state.sanitize_update(
                ctx=self.ctx,
                update={
                    "agents_thoughts": [
                        "No structured decisions found, I cannot execute anything."
                    ],
                    "execution_depth": new_depth,
                },
                agent="executor",
            )

        system_message = Template(
            Path(__file__).parent.joinpath("executor.md").read_text(encoding="utf-8")
        ).render(platform=self.ctx.device.mobile_platform.value)
        
        # HAL3000Android: Enhance with knowledge base context
        from minitap.mobile_use.utils.knowledge_base import enhance_agent_prompt
        system_message = enhance_agent_prompt("executor", system_message)
        cortex_last_thought = (
            state.cortex_last_thought if state.cortex_last_thought else state.agents_thoughts[-1]
        )
        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=cortex_last_thought),
            HumanMessage(content=structured_decisions),
            *state.executor_messages,
        ]

        llm = get_llm(ctx=self.ctx, name="executor")
        
        if hasattr(llm, "is_cerebras"):
            # Cerebras path - manual tool calling via JSON
            tools = get_tools_from_wrappers(self.ctx, EXECUTOR_WRAPPERS_TOOLS)
            
            # Create comprehensive tool descriptions for Cerebras
            tools_description = """
Available tools for execution:

1. **tap**: Tap on a UI element
   - Parameters: {"selector_request": {"text": "element_text"}, "agent_thought": "description", "index": null}
   - Example: {"name": "tap", "parameters": {"selector_request": {"text": "Settings"}, "agent_thought": "Tapping Settings icon"}}

2. **long_press_on**: Long press on a UI element  
   - Parameters: {"selector_request": {"text": "element_text"}, "agent_thought": "description", "index": null}
   - Example: {"name": "long_press_on", "parameters": {"selector_request": {"text": "App Icon"}, "agent_thought": "Long pressing app icon"}}

3. **swipe**: Swipe gesture on screen
   - Parameters: {"swipe_request": {"direction": "up/down/left/right", "start_coordinate": [x,y], "end_coordinate": [x,y]}, "agent_thought": "description"}
   - Example: {"name": "swipe", "parameters": {"swipe_request": {"direction": "up"}, "agent_thought": "Scrolling up"}}

4. **input_text**: Type text into focused input field
   - Parameters: {"text": "text_to_type", "agent_thought": "description"}
   - Example: {"name": "input_text", "parameters": {"text": "Hello World", "agent_thought": "Typing message"}}

5. **copy_text_from**: Copy text from a UI element
   - Parameters: {"selector_request": {"text": "element_text"}, "agent_thought": "description"}
   - Example: {"name": "copy_text_from", "parameters": {"selector_request": {"text": "Copy this"}, "agent_thought": "Copying text"}}

6. **paste_text**: Paste previously copied text
   - Parameters: {"agent_thought": "description"}
   - Example: {"name": "paste_text", "parameters": {"agent_thought": "Pasting copied text"}}

7. **erase_one_char**: Delete characters from input field
   - Parameters: {"nb_chars": 1, "agent_thought": "description"}
   - Example: {"name": "erase_one_char", "parameters": {"nb_chars": 3, "agent_thought": "Deleting 3 characters"}}

8. **launch_app**: Launch an app by package name
   - Parameters: {"package_name": "com.example.app", "agent_thought": "description"}
   - Example: {"name": "launch_app", "parameters": {"package_name": "com.android.settings", "agent_thought": "Opening Settings app"}}

9. **stop_app**: Stop/close an app
   - Parameters: {"package_name": "com.example.app", "agent_thought": "description"}
   - Example: {"name": "stop_app", "parameters": {"package_name": "com.android.chrome", "agent_thought": "Closing Chrome"}}

10. **open_link**: Open a URL/link
    - Parameters: {"url": "https://example.com", "agent_thought": "description"}
    - Example: {"name": "open_link", "parameters": {"url": "https://google.com", "agent_thought": "Opening Google"}}

11. **back**: Press the back button
    - Parameters: {"agent_thought": "description"}
    - Example: {"name": "back", "parameters": {"agent_thought": "Going back to previous screen"}}

12. **press_key**: Press a hardware key
    - Parameters: {"key": "HOME/BACK/MENU/POWER", "agent_thought": "description"}
    - Example: {"name": "press_key", "parameters": {"key": "HOME", "agent_thought": "Going to home screen"}}

13. **wait_for_animation_to_end**: Wait for animations to complete
    - Parameters: {"timeout": 10.0, "agent_thought": "description"}
    - Example: {"name": "wait_for_animation_to_end", "parameters": {"timeout": 5.0, "agent_thought": "Waiting for loading"}}

14. **glimpse_screen**: Take a screenshot
    - Parameters: {"agent_thought": "description"}
    - Example: {"name": "glimpse_screen", "parameters": {"agent_thought": "Taking screenshot to analyze"}}
"""
            
            # Add tool information to system message
            enhanced_system_message = system_message + f"""

{tools_description}

You must respond with a JSON object containing tool calls to execute. Format:
{{
    "tool_calls": [
        {{
            "name": "tool_name",
            "parameters": {{"param1": "value1", "param2": "value2"}}
        }}
    ],
    "reasoning": "Brief explanation of why you're calling these tools"
}}

IMPORTANT: 
- Always call exactly ONE tool to execute the action described in the structured decisions.
- Use the exact parameter names and formats shown in the examples above.
- For selector_request, always use {{"text": "element_text"}} format to select UI elements by their text.
- Include meaningful agent_thought explaining what you're doing.
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
            
            print(f"[DEBUG] Cerebras executor response: {response_obj.content}")
            
            # Parse the JSON response and execute tools
            import json
            from langchain_core.messages import AIMessage, ToolMessage
            
            try:
                tool_response = json.loads(response_obj.content)
                print(f"[DEBUG] Parsed tool response: {tool_response}")
                
                tool_calls = tool_response.get("tool_calls", [])
                reasoning = tool_response.get("reasoning", "")
                
                print(f"[DEBUG] Tool calls found: {len(tool_calls)}")
                print(f"[DEBUG] Tool calls: {tool_calls}")
                print(f"[DEBUG] Reasoning: {reasoning}")
                
                # Create tool call messages
                response_messages = []
                if reasoning:
                    response_messages.append(AIMessage(content=reasoning))
                
                # Execute each tool call
                for i, tool_call in enumerate(tool_calls):
                    tool_name = tool_call["name"]
                    tool_params = tool_call["parameters"]
                    
                    print(f"[DEBUG] Executing tool {i+1}/{len(tool_calls)}: {tool_name}")
                    print(f"[DEBUG] Tool parameters: {tool_params}")
                    
                    # Find the tool
                    tool_to_call = None
                    for tool in tools:
                        if tool.name == tool_name:
                            tool_to_call = tool
                            break
                    
                    if tool_to_call:
                        print(f"[DEBUG] Found tool: {tool_to_call.name}")
                        # For Cerebras, call the underlying controller directly instead of LangChain wrapper
                        try:
                            print(f"[DEBUG] Calling tool directly with params: {tool_params}")
                            
                            # Import all the controllers and types
                            from minitap.mobile_use.controllers.mobile_command_controller import (
                                tap as tap_controller,
                                long_press_on as long_press_controller,
                                swipe as swipe_controller,
                                input_text as input_text_controller,
                                copy_text_from as copy_text_controller,
                                paste_text as paste_text_controller,
                                erase_text as erase_text_controller,
                                launch_app as launch_app_controller,
                                stop_app as stop_app_controller,
                                open_link as open_link_controller,
                                back as back_controller,
                                press_key as press_key_controller,
                                wait_for_animation_to_end as wait_controller,
                                take_screenshot as screenshot_controller,
                                TextSelectorRequest,
                                IdSelectorRequest,
                                CoordinatesSelectorRequest,
                                PercentagesSelectorRequest,
                                SelectorRequestWithCoordinates,
                                SelectorRequestWithPercentages,
                                IdWithTextSelectorRequest,
                                SwipeRequest,
                                Key
                            )
                            
                            def create_selector_request(data):
                                """Create the appropriate selector request type based on the data"""
                                if "text" in data:
                                    return TextSelectorRequest(**data)
                                elif "id" in data and "text" in data:
                                    return IdWithTextSelectorRequest(**data)
                                elif "id" in data:
                                    return IdSelectorRequest(**data)
                                elif "coordinates" in data:
                                    return SelectorRequestWithCoordinates(**data)
                                elif "percentages" in data:
                                    return SelectorRequestWithPercentages(**data)
                                else:
                                    # Default to text selector if unclear
                                    return TextSelectorRequest(**data)
                            
                            agent_thought = tool_params.get("agent_thought", "")
                            result = None
                            result_msg = ""
                            
                            if tool_name == "tap":
                                selector_request_data = tool_params.get("selector_request", {})
                                index = tool_params.get("index", None)
                                selector_request = create_selector_request(selector_request_data)
                                result = tap_controller(ctx=self.ctx, selector_request=selector_request, index=index)
                                if result is None:
                                    result_msg = f"Successfully tapped on element with {selector_request_data}"
                                    print(f"[DEBUG] Tap successful!")
                                else:
                                    result_msg = f"Failed to tap: {result}"
                                    print(f"[DEBUG] Tap failed: {result}")
                                    
                            elif tool_name == "long_press_on":
                                selector_request_data = tool_params.get("selector_request", {})
                                index = tool_params.get("index", None)
                                selector_request = create_selector_request(selector_request_data)
                                result = long_press_controller(ctx=self.ctx, selector_request=selector_request, index=index)
                                if result is None:
                                    result_msg = f"Successfully long pressed on element with {selector_request_data}"
                                else:
                                    result_msg = f"Failed to long press: {result}"
                                    
                            elif tool_name == "swipe":
                                swipe_request_data = tool_params.get("swipe_request", {})
                                swipe_request = SwipeRequest(**swipe_request_data)
                                result = swipe_controller(ctx=self.ctx, swipe_request=swipe_request)
                                if result is None:
                                    result_msg = f"Successfully swiped {swipe_request_data}"
                                else:
                                    result_msg = f"Failed to swipe: {result}"
                                    
                            elif tool_name == "input_text":
                                text = tool_params.get("text", "")
                                result = input_text_controller(ctx=self.ctx, text=text)
                                if result is None:
                                    result_msg = f"Successfully input text: '{text}'"
                                else:
                                    result_msg = f"Failed to input text: {result}"
                                    
                            elif tool_name == "copy_text_from":
                                selector_request_data = tool_params.get("selector_request", {})
                                selector_request = create_selector_request(selector_request_data)
                                result = copy_text_controller(ctx=self.ctx, selector_request=selector_request)
                                if result is None:
                                    result_msg = f"Successfully copied text from element with {selector_request_data}"
                                else:
                                    result_msg = f"Failed to copy text: {result}"
                                    
                            elif tool_name == "paste_text":
                                result = paste_text_controller(ctx=self.ctx)
                                if result is None:
                                    result_msg = "Successfully pasted text"
                                else:
                                    result_msg = f"Failed to paste text: {result}"
                                    
                            elif tool_name == "erase_one_char":
                                nb_chars = tool_params.get("nb_chars", 1)
                                result = erase_text_controller(ctx=self.ctx, nb_chars=nb_chars)
                                if result is None:
                                    result_msg = f"Successfully erased {nb_chars} character(s)"
                                else:
                                    result_msg = f"Failed to erase characters: {result}"
                                    
                            elif tool_name == "launch_app":
                                package_name = tool_params.get("package_name", "")
                                result = launch_app_controller(ctx=self.ctx, package_name=package_name)
                                if result is None:
                                    result_msg = f"Successfully launched app: {package_name}"
                                else:
                                    result_msg = f"Failed to launch app: {result}"
                                    
                            elif tool_name == "stop_app":
                                package_name = tool_params.get("package_name", None)
                                result = stop_app_controller(ctx=self.ctx, package_name=package_name)
                                if result is None:
                                    result_msg = f"Successfully stopped app: {package_name}"
                                else:
                                    result_msg = f"Failed to stop app: {result}"
                                    
                            elif tool_name == "open_link":
                                url = tool_params.get("url", "")
                                result = open_link_controller(ctx=self.ctx, url=url)
                                if result is None:
                                    result_msg = f"Successfully opened link: {url}"
                                else:
                                    result_msg = f"Failed to open link: {result}"
                                    
                            elif tool_name == "back":
                                result = back_controller(ctx=self.ctx)
                                if result is None:
                                    result_msg = "Successfully pressed back button"
                                else:
                                    result_msg = f"Failed to press back: {result}"
                                    
                            elif tool_name == "press_key":
                                key_name = tool_params.get("key", "")
                                try:
                                    key = Key(key_name)
                                    result = press_key_controller(ctx=self.ctx, key=key)
                                    if result is None:
                                        result_msg = f"Successfully pressed key: {key_name}"
                                    else:
                                        result_msg = f"Failed to press key: {result}"
                                except ValueError:
                                    result_msg = f"Invalid key: {key_name}"
                                    
                            elif tool_name == "wait_for_animation_to_end":
                                timeout = tool_params.get("timeout", 10.0)
                                result = wait_controller(ctx=self.ctx, timeout=timeout)
                                if result is None:
                                    result_msg = f"Successfully waited for animations to end (timeout: {timeout}s)"
                                else:
                                    result_msg = f"Wait for animation failed: {result}"
                                    
                            elif tool_name == "glimpse_screen":
                                result = screenshot_controller(ctx=self.ctx)
                                if result:
                                    result_msg = "Successfully took screenshot"
                                else:
                                    result_msg = "Failed to take screenshot"
                                    
                            else:
                                # For unknown tools, try the LangChain format as fallback
                                tool_call_format = {
                                    "name": tool_name,
                                    "args": tool_params,
                                    "type": "tool_call",
                                    "tool_call_id": f"call_{tool_name}_{i}"
                                }
                                print(f"[DEBUG] Unknown tool, using LangChain format: {tool_call_format}")
                                result = await tool_to_call.ainvoke(tool_call_format)
                                result_msg = str(result)
                            
                            print(f"[DEBUG] Tool execution result: {result_msg}")
                            response_messages.append(ToolMessage(
                                content=result_msg,
                                tool_call_id=f"call_{tool_name}_{i}",
                                name=tool_name
                            ))
                                
                        except Exception as e:
                            print(f"[DEBUG] Tool execution error: {str(e)}")
                            import traceback
                            print(f"[DEBUG] Full traceback: {traceback.format_exc()}")
                            response_messages.append(ToolMessage(
                                content=f"Error executing {tool_name}: {str(e)}",
                                tool_call_id=f"call_{tool_name}_{i}",
                                name=tool_name
                            ))
                    else:
                        print(f"[DEBUG] Tool not found: {tool_name}")
                        print(f"[DEBUG] Available tools: {[t.name for t in tools]}")
                
                response = response_messages
                print(f"[DEBUG] Final response messages: {len(response_messages)}")
            
            except Exception as e:
                print(f"[DEBUG] JSON parsing error: {str(e)}")
                # Fallback if JSON parsing fails
                response = [AIMessage(content=f"Failed to parse tool response: {str(e)}")]
        
        else:
            # LangChain path - standard tool binding
            llm_bind_tools_kwargs: dict = {
                "tools": get_tools_from_wrappers(self.ctx, EXECUTOR_WRAPPERS_TOOLS),
            }

            # ChatGoogleGenerativeAI does not support the "parallel_tool_calls" keyword
            if not isinstance(llm, ChatGoogleGenerativeAI | ChatVertexAI):
                llm_bind_tools_kwargs["parallel_tool_calls"] = True

            llm = llm.bind_tools(**llm_bind_tools_kwargs)
            response = await llm.ainvoke(messages)

        return state.sanitize_update(
            ctx=self.ctx,
            update={
                "cortex_last_thought": cortex_last_thought,
                EXECUTOR_MESSAGES_KEY: response if isinstance(response, list) else [response],
                "execution_depth": new_depth,
            },
            agent="executor",
        )
