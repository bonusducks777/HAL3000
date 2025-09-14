# mobile-use SDK Examples

Location: `src/mobile_use/sdk/examples/`

Run any example via:
- `python src/mobile_use/sdk/examples/<filename>.py`

## Practical Automation Examples

These examples demonstrate two different ways to use the SDK, each applying an appropriate level of complexity for the task at hand:

### simple_photo_organizer.py - Straightforward Approach

Demonstrates the simplest way to use the SDK for quick automation tasks:

- **Direct API calls** without builders or complex configuration
- Creates a photo album and organizes photos from a specific date
- Uses structured Pydantic output to capture results

### smart_notification_assistant.py - Feature-Rich Approach

Showcases more advanced SDK features while remaining practical:

- Uses builder pattern for configuring the agent and overriding the default task configurations
- Implements **multiple specialized agent profiles** for different reasoning tasks:
  - Analyzer profile for detailed inspection of notifications
  - Note taker profile for writing a summary of the notifications
- Enables **tracing** for debugging and visualization
- Includes **structured Pydantic models** with enums and nested relationships
- Demonstrates proper **exception handling** for different error types
- Shows how to set up task defaults for consistent configuration

## Usage Notes

- **Choosing an Approach**: Use the direct approach (like in `simple_photo_organizer.py`) for simple tasks and the builder approach (like in `smart_notification_assistant.py`) when you need more customization.

- **Device Detection**: The agent detects the first available device unless you specify one with `AgentConfigBuilder.for_device(...)`.

- **Servers**: With default base URLs (`localhost:9998/9999`), the agent starts the servers automatically. When you override URLs, it assumes servers are already running.

- **LLM API Keys**: Provide necessary keys (e.g., `OPENAI_API_KEY`) in a `.env` file at repo root; see `mobile_use/config.py`.

- **Traces**: When enabled, traces are saved to a specified directory (defaulting to `./mobile-use-traces/`) and can be useful for debugging and visualization.

- **Structured Output**: Pydantic models enable type safety when processing task outputs, making it easier to handle and chain results between tasks.
