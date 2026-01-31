import typer
from typing import Optional
from hecaton.client.managers.server import ServerManager
from hecaton.client.managers.api import HecatonServer

user_app = typer.Typer()

@user_app.command("create")
def create_user(
    ctx: typer.Context,
    username: str = typer.Option(..., prompt="NEW Username", help="Username for the new user"),
    password: str = typer.Option(..., prompt="NEW Password", hide_input=True, help="Password for the new user"),
    role: str = typer.Option("user", help="Role (admin/user/worker)")
):
    """
    Create a new user on the connected server (Requires Admin privileges).
    """
    mgr: ServerManager = ctx.obj["server_mgr"]
    try:
        server = mgr.connected_server()
        
        # We need the token/secret of the currently connected user (who must be admin)
        if not server.token:
            typer.echo("Error: You must be logged in to create users.")
            return

        message = HecatonServer.create_user(
            ip=server.ip,
            secret=server.token,
            username=username,
            password=password,
            role=role
        )
        typer.echo(message)
    except Exception as e:
        typer.echo(f"Error: {e}")
