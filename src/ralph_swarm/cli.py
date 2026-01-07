"""Ralph Swarm CLI - Main entry point."""

import click
from rich.console import Console

from ralph_swarm.commands import build, cleanup, init, plan, specify, status

console = Console()


@click.group()
@click.version_option()
def main() -> None:
    """Ralph Swarm - AI-powered autonomous development orchestrator.

    Phases:
      init    - Interactive project setup (objective, tech stack)
      specify - Build specifications interactively (V0 scope)
      plan    - Planning mode (create epics, stories from specs)
      build   - Build mode (implement issues with worker swarm)

    Utilities:
      status  - Show project progress and worker status
      cleanup - Clean up orphaned work from crashed workers
    """
    pass


main.add_command(init.init_cmd, name="init")
main.add_command(specify.specify_cmd, name="specify")
main.add_command(plan.plan_cmd, name="plan")
main.add_command(build.build_cmd, name="build")
main.add_command(status.status_cmd, name="status")
main.add_command(cleanup.cleanup_cmd, name="cleanup")


if __name__ == "__main__":
    main()
