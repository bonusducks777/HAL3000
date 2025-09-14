#!/usr/bin/env python3
"""
HAL3000Android - Custom entry point for mobile automation
Wraps the original mobile-use-main functionality with our enhancements:
- Multi-model support via .env configuration
- Knowledge base integration
- Single entry point interface
"""

import os
import sys
import asyncio
import typer
from typing import Annotated, Optional
from rich.console import Console
from pathlib import Path

# Add the project root to Python path so minitap imports work
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from minitap.mobile_use.main import run_automation

app = typer.Typer(add_completion=False, pretty_exceptions_enable=False)
console = Console()

@app.command()
def main(
    goal: Annotated[str | None, typer.Argument(help="The main goal for the agent to achieve.")] = None,
    test_name: Annotated[
        str | None,
        typer.Option(
            "--test-name",
            "-n",
            help="A name for the test recording. If provided, a trace will be saved.",
        ),
    ] = None,
    traces_path: Annotated[
        str,
        typer.Option(
            "--traces-path",
            "-p",
            help="The path to save the traces.",
        ),
    ] = "traces",
    output_description: Annotated[
        str | None,
        typer.Option(
            "--output-description",
            "-o",
            help="A dict output description for the agent.",
        ),
    ] = None,
    device_id: Annotated[
        str | None,
        typer.Option(
            "--device",
            "-d",
            help="Specific device ID to use (auto-detected if not provided)",
        ),
    ] = None,
):
    """
    HAL3000Android - Enhanced mobile automation system
    
    Runs mobile automation tasks with multi-model support and knowledge base integration.
    """
    
    # Load our custom .env file if it exists
    env_file = current_dir / ".env"
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        console.print(f"[green]✓[/green] Loaded HAL3000Android configuration from {env_file}")
    
    # Display our custom banner
    console.print("""
[bold blue]HAL3000Android[/bold blue] [bold white]Mobile Automation System[/bold white]
[dim]Enhanced mobile-use-main with multi-model support and knowledge base[/dim]
    """)
    
    # Display configuration info
    planner_provider = os.getenv("PLANNER_PROVIDER", "openai")
    planner_model = os.getenv("PLANNER_MODEL", "gpt-5-mini")
    cortex_provider = os.getenv("CORTEX_PROVIDER", "openai")
    cortex_model = os.getenv("CORTEX_MODEL", "gpt-4o-mini") 
    contextor_provider = os.getenv("CONTEXTOR_PROVIDER", "openai")
    contextor_model = os.getenv("CONTEXTOR_MODEL", "gpt-4o-mini")
    executor_provider = os.getenv("EXECUTOR_PROVIDER", "openai")
    executor_model = os.getenv("EXECUTOR_MODEL", "gpt-5-mini")
    orchestrator_provider = os.getenv("ORCHESTRATOR_PROVIDER", "openai")
    orchestrator_model = os.getenv("ORCHESTRATOR_MODEL", "gpt-5-mini")
    
    console.print(f"[dim]Planner: {planner_provider}/{planner_model} | Contextor: {contextor_provider}/{contextor_model} | Cortex: {cortex_provider}/{cortex_model} | Executor: {executor_provider}/{executor_model} | Orchestrator: {orchestrator_provider}/{orchestrator_model}[/dim]")
    
    # Interactive goal input if not provided
    if not goal:
        console.print()
        console.print("[bold cyan]🎯 What would you like the agent to accomplish?[/bold cyan]")
        console.print("[dim]Examples:[/dim]")
        console.print("[dim]  • 'Open Instagram and like the latest post'[/dim]")
        console.print("[dim]  • 'Send a WhatsApp message to John saying hello'[/dim]")
        console.print("[dim]  • 'Take a screenshot of the current screen'[/dim]")
        console.print("[dim]  • 'Navigate to Settings and enable dark mode'[/dim]")
        console.print()
        
        try:
            goal = typer.prompt("Enter your goal", type=str)
            if not goal.strip():
                console.print("[red]Error: Goal cannot be empty[/red]")
                sys.exit(1)
            goal = goal.strip()
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
            sys.exit(0)
    
    # Check for knowledge base
    kb_file = current_dir / "knowledgebase.json"
    if kb_file.exists():
        console.print(f"[green]✓[/green] Knowledge base loaded from {kb_file}")
    else:
        console.print("[yellow]![/yellow] No knowledge base found (knowledgebase.json)")
    
    # Display goal confirmation
    console.print()
    console.print(f"[bold green]🚀 Ready to execute:[/bold green] [bold white]{goal}[/bold white]")
    
    # Optional confirmation prompt for interactive mode
    if not any([test_name, output_description]):  # Only prompt if this seems like an interactive session
        console.print("[dim]Press Ctrl+C to cancel, or Enter to continue...[/dim]")
        try:
            input()
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
            sys.exit(0)
    
    console.print()
    
    # Run the original automation system
    try:
        asyncio.run(
            run_automation(
                goal=goal,
                test_name=test_name,
                traces_output_path_str=traces_path,
                output_description=output_description,
            )
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Automation interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    app()