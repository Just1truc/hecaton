from __future__ import annotations

import typer

from hecaton.client.managers.api import HecatonServer
from hecaton.client.managers.server import ServerManager

worker_app = typer.Typer()


@worker_app.command("list")
def list_workers(ctx: typer.Context):
    """
    List all workers and their status.
    """
    mgr: ServerManager = ctx.obj["server_mgr"]
    try:
        server = mgr.connected_server()
        if not server.token and not server.secret:
            typer.echo("Error: You must be logged in.")
            return

        # token takes precedence, but fallback to secret for legacy (though legacy secret is usually for workers)
        auth_token = server.token if server.token else server.secret

        workers = HecatonServer.list_workers(ip=server.ip, secret=auth_token)

        if isinstance(workers, str):
            typer.echo(f"Error: {workers}")
            return

        # workers is a list of lists/tuples: [[id, status, updated_at], ...]
        if not workers:
            typer.echo("No workers found.")
            return

        typer.echo(f"{'ID':<40} {'STATUS':<15} {'GPU':<25} {'LAST SEEN'}")
        typer.echo("-" * 105)
        for w in workers:
            w_id, status, updated_at, gpu_name = w
            display_gpu = gpu_name if gpu_name else "N/A"
            typer.echo(f"{w_id:<40} {status:<15} {display_gpu:<25} {updated_at}")

    except Exception as e:
        typer.echo(f"Error: {e}")
