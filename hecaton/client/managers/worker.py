import typer
import json
from hecaton.client.managers.server import ServerManager
from hecaton.client.managers.api import HecatonServer

worker_app = typer.Typer()

@worker_app.command("list")
def list_workers(
    ctx: typer.Context
):
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

        workers = HecatonServer.list_workers(
            ip=server.ip,
            secret=auth_token
        )
        
        if isinstance(workers, str):
            typer.echo(f"Error: {workers}")
            return

        # workers is a list of lists/tuples: [[id, status, updated_at], ...]
        if not workers:
            typer.echo("No workers found.")
            return

        typer.echo(f"{'ID':<40} {'STATUS':<15} {'LAST SEEN'}")
        typer.echo("-" * 80)
        for w in workers:
            # w structure depends on SQL query: SELECT * FROM workers
            # workers table: id TEXT PRIMARY KEY, status TEXT, updated_at TEXT
            w_id, status, updated_at = w
            typer.echo(f"{w_id:<40} {status:<15} {updated_at}")

    except Exception as e:
        typer.echo(f"Error: {e}")
