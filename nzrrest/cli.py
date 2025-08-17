"""
CLI tool for nzrRest framework using Typer
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table

app = typer.Typer(
    name="nzrrest",
    help="nzrRest Framework CLI - Build AI APIs with MCP support",
    rich_markup_mode="rich",
)
console = Console()


@app.command()
def new(
    project_name: str = typer.Argument(..., help="Name of the new project"),
    template: str = typer.Option("mcp-server", help="Template to use"),
    directory: Optional[str] = typer.Option(None, "--dir", "-d", help="Target directory"),
    force: bool = typer.Option(False, "--force", "-f", help="Force creation even if directory exists"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Interactive mode"),
):
    """Create a new nzrRest project from template"""

    # Determine target directory
    if directory:
        target_dir = Path(directory) / project_name
    else:
        target_dir = Path.cwd() / project_name

    # Check if directory exists
    if target_dir.exists() and not force:
        if not Confirm.ask(f"Directory '{target_dir}' already exists. Continue?"):
            raise typer.Abort()

    # Interactive configuration
    config = {}
    if interactive:
        config = _interactive_project_config(project_name, template)
    else:
        config = _default_project_config(project_name, template)

    # Create project
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating project...", total=None)

        _create_project_from_template(target_dir, template, config)

        progress.update(task, description="Installing dependencies...")
        _install_dependencies(target_dir, config.get("install_deps", True))

        progress.update(task, description="Initializing git repository...")
        if config.get("init_git", True):
            _init_git_repo(target_dir)

    # Success message
    console.print(
        Panel(
            f"""🎉 Project '{project_name}' created successfully!

📁 Location: {target_dir}
🚀 Template: {template}

Next steps:
1. cd {project_name}
2. nzrrest run --reload
3. Visit http://localhost:8000/health

Documentation: https://nzrrest.readthedocs.io
        """,
            title="Success",
            border_style="green",
        )
    )


@app.command()
def run(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
    workers: int = typer.Option(1, help="Number of worker processes"),
    log_level: str = typer.Option("info", help="Log level"),
    config_file: Optional[str] = typer.Option(None, help="Config file path"),
):
    """Run the nzrRest development server"""

    # Check if we're in a nzrRest project
    if not _is_nzrrest_project():
        console.print("[red]Error: Not a nzrRest project. Run 'nzrrest new' to create one.[/red]")
        raise typer.Exit(1)

    # Build uvicorn command
    cmd = [
        "uvicorn",
        "main:app",
        "--host",
        host,
        "--port",
        str(port),
        "--log-level",
        log_level,
    ]

    if reload:
        cmd.append("--reload")

    if workers > 1 and not reload:
        cmd.extend(["--workers", str(workers)])

    console.print(f"[green]Starting nzrRest server on {host}:{port}[/green]")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Server failed to start: {e}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")


@app.command()
def migrate(
    message: Optional[str] = typer.Option(None, "-m", "--message", help="Migration message"),
    auto: bool = typer.Option(False, help="Auto-generate migration"),
    upgrade: bool = typer.Option(False, help="Run upgrade after generating"),
    downgrade: Optional[str] = typer.Option(None, help="Downgrade to specific revision"),
):
    """Database migration commands"""

    if not _is_nzrrest_project():
        console.print("[red]Error: Not a nzrRest project.[/red]")
        raise typer.Exit(1)

    if downgrade:
        cmd = ["alembic", "downgrade", downgrade]
        console.print(f"[yellow]Downgrading to {downgrade}...[/yellow]")
    elif upgrade:
        cmd = ["alembic", "upgrade", "head"]
        console.print("[green]Running database upgrade...[/green]")
    else:
        if not message and not auto:
            message = Prompt.ask("Migration message")

        if auto:
            cmd = ["alembic", "revision", "--autogenerate"]
            if message:
                cmd.extend(["-m", message])
        else:
            cmd = ["alembic", "revision", "-m", message or "New migration"]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        console.print("[green]Migration completed successfully[/green]")
        if result.stdout:
            console.print(result.stdout)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Migration failed: {e}[/red]")
        if e.stderr:
            console.print(e.stderr)
        raise typer.Exit(1)


@app.command()
def models(
    list_models: bool = typer.Option(False, "--list", "-l", help="List available models"),
    add_model: Optional[str] = typer.Option(None, "--add", help="Add a new model"),
    model_type: Optional[str] = typer.Option(None, "--type", help="Model type"),
    config_file: Optional[str] = typer.Option("config.py", help="Config file to update"),
):
    """Manage AI models"""

    if not _is_nzrrest_project():
        console.print("[red]Error: Not a nzrRest project.[/red]")
        raise typer.Exit(1)

    if list_models:
        _list_project_models()
    elif add_model:
        if not model_type:
            model_type = Prompt.ask("Model type", choices=["openai", "anthropic", "huggingface", "mock"])
        _add_model_to_config(add_model, model_type, config_file)
    else:
        console.print("Use --list to see models or --add to add a new model")


@app.command()
def info():
    """Show project information"""

    if not _is_nzrrest_project():
        console.print("[red]Error: Not a nzrRest project.[/red]")
        raise typer.Exit(1)

    # Read project info
    project_info = _get_project_info()

    table = Table(title="Project Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    for key, value in project_info.items():
        table.add_row(key, str(value))

    console.print(table)


@app.command()
def version():
    """Show nzrRest version"""
    from . import __version__

    console.print(f"nzrRest Framework v{__version__}")


def _interactive_project_config(project_name: str, template: str) -> dict:
    """Interactive project configuration"""

    console.print(f"\n[bold blue]Configuring nzrRest project '{project_name}'[/bold blue]")

    config = {
        "project_name": project_name,
        "template": template,
        "description": Prompt.ask("Project description", default="AI API built with nzrRest"),
        "author": Prompt.ask("Author name", default="Your Name"),
        "email": Prompt.ask("Author email", default="your.email@example.com"),
        "python_version": Prompt.ask("Python version", default="3.8"),
        "install_deps": Confirm.ask("Install dependencies?", default=True),
        "init_git": Confirm.ask("Initialize git repository?", default=True),
    }

    # Template-specific configuration
    if template == "mcp-server":
        config.update(
            {
                "include_database": Confirm.ask("Include database support?", default=True),
                "include_auth": Confirm.ask("Include authentication?", default=False),
                "include_cors": Confirm.ask("Include CORS middleware?", default=True),
                "default_model": Prompt.ask(
                    "Default AI model",
                    default="mock",
                    choices=["mock", "openai", "anthropic"],
                ),
            }
        )

    return config


def _default_project_config(project_name: str, template: str) -> dict:
    """Default project configuration"""
    return {
        "project_name": project_name,
        "template": template,
        "description": "AI API built with nzrRest",
        "author": "Your Name",
        "email": "your.email@example.com",
        "python_version": "3.8",
        "install_deps": True,
        "init_git": True,
        "include_database": True,
        "include_auth": False,
        "include_cors": True,
        "default_model": "mock",
    }


def _create_project_from_template(target_dir: Path, template: str, config: dict):
    """Create project from template"""

    # Get template directory
    template_dir = Path(__file__).parent.parent / "templates" / template

    if not template_dir.exists():
        console.print(f"[red]Template '{template}' not found[/red]")
        raise typer.Exit(1)

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)

    # Copy template files
    for item in template_dir.rglob("*"):
        if item.is_file():
            # Calculate relative path
            rel_path = item.relative_to(template_dir)
            target_file = target_dir / rel_path

            # Create parent directories
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # Process template files
            if item.suffix in [".py", ".txt", ".md", ".toml", ".yaml", ".yml"]:
                _process_template_file(item, target_file, config)
            else:
                shutil.copy2(item, target_file)


def _process_template_file(source: Path, target: Path, config: dict):
    """Process template file with variable substitution"""

    with open(source, "r", encoding="utf-8") as f:
        content = f.read()

    # Simple template variable substitution
    for key, value in config.items():
        placeholder = f"{{{{ {key} }}}}"
        content = content.replace(placeholder, str(value))

    with open(target, "w", encoding="utf-8") as f:
        f.write(content)


def _install_dependencies(project_dir: Path, install: bool):
    """Install project dependencies"""

    if not install:
        return

    requirements_file = project_dir / "requirements.txt"
    if requirements_file.exists():
        try:
            subprocess.run(
                ["pip", "install", "-r", str(requirements_file)],
                check=True,
                cwd=project_dir,
            )
        except subprocess.CalledProcessError:
            console.print("[yellow]Warning: Failed to install dependencies[/yellow]")


def _init_git_repo(project_dir: Path):
    """Initialize git repository"""

    try:
        subprocess.run(["git", "init"], check=True, cwd=project_dir, capture_output=True)
        subprocess.run(["git", "add", "."], check=True, cwd=project_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit: nzrRest project"],
            check=True,
            cwd=project_dir,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        console.print("[yellow]Warning: Failed to initialize git repository[/yellow]")


def _is_nzrrest_project() -> bool:
    """Check if current directory is a nzrRest project"""

    indicators = [Path("main.py"), Path("config.py"), Path("requirements.txt")]

    return any(indicator.exists() for indicator in indicators)


def _get_project_info() -> dict:
    """Get project information"""

    info = {}

    # Read from main.py if it exists
    main_file = Path("main.py")
    if main_file.exists():
        info["Main file"] = str(main_file)

    # Read from config.py if it exists
    config_file = Path("config.py")
    if config_file.exists():
        info["Config file"] = str(config_file)

    # Read requirements
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        with open(requirements_file) as f:
            deps = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            info["Dependencies"] = str(len(deps))

    # Check git
    if Path(".git").exists():
        info["Git repository"] = "Yes"

    return info


def _list_project_models():
    """List models in the current project"""

    try:
        # Try to import config and get models
        import sys

        sys.path.insert(0, str(Path.cwd()))

        from config import AI_MODELS_CONFIG

        if "models" in AI_MODELS_CONFIG:
            table = Table(title="Configured AI Models")
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Auto Load", style="yellow")

            for model in AI_MODELS_CONFIG["models"]:
                table.add_row(
                    model["name"],
                    model["type"],
                    "Yes" if model.get("auto_load", False) else "No",
                )

            console.print(table)
        else:
            console.print("[yellow]No models configured[/yellow]")

    except Exception as e:
        console.print(f"[red]Error reading models configuration: {e}[/red]")


def _add_model_to_config(model_name: str, model_type: str, config_file: str):
    """Add a model to the configuration file"""

    console.print(f"[green]Adding model '{model_name}' of type '{model_type}' to {config_file}[/green]")

    # This is a simplified implementation
    # In practice, you'd need to parse and modify the Python config file
    model_config = f"""
# Added by nzrrest CLI
{{
    "name": "{model_name}",
    "type": "{model_type}",
    "auto_load": False,
    "config": {{
        # Add your model configuration here
    }}
}},
"""

    console.print("Add this configuration to your AI_MODELS_CONFIG:")
    console.print(Syntax(model_config, "python", theme="monokai"))


if __name__ == "__main__":
    app()
