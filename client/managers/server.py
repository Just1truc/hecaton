import typer
import click
from typing import Optional, List
from client.managers.db import with_locked_db, ServerInfo

server_app = typer.Typer()

class ServerManager:
    
    def __init__(self):
        self.selected_server = None
        
    def list_servers(self) -> List[str]:
        with with_locked_db() as db:
            return sorted([server.name for server in db.servers])
        
    def register_server(
        self,
        ip : str,
        name : str,
        secret : str
    ):
        with with_locked_db(mutate=True) as db:
            found = False
            for server in db.servers:
                if server.name == name:
                    server.ip = ip or server.ip
                    server.secret = secret or server.secret
                    found = True
            if not found:
                db.servers.append(ServerInfo(ip=ip, name=name, secret=secret))
            
    def server_name_exists(
        self,
        server_name : str
    ):
        return server_name in self.list_servers()
    
    def server_info(
        self,
        server_name : str
    ):  
        with with_locked_db() as db:
            for server in db.servers:
                if server.name == server_name:
                    return server
                
    def connected_server(
        self
    ):
        if self.selected_server == None:
            raise Exception('error: Not connected to a server')
        else:
            return self.server_info(self.selected_server)
        
@server_app.command("list")
def server_list(ctx : typer.Context):
    mgr : ServerManager = ctx.obj["server_mgr"]
    if len(mgr.list_servers()):
        typer.echo("\n".join(mgr.list_servers()))
        
@server_app.command("new")
def register(
    ctx : typer.Context,
    ip : str = typer.Option(None, prompt="    Server IP", help= "Server IP"),
    name : str = typer.Option(None, prompt="    Local name", help= "Local name"),
    secret : str = typer.Option(None, prompt="    Secret", help= "Local name")
):
    mgr : ServerManager = ctx.obj["server_mgr"]
    mgr.register_server(ip, name, secret)
    
@server_app.command("help")
def server_help():
    typer.echo('\n'.join(open("help.txt").read().split("\n")[12:19]))
    
def complete_server_name(ctx : typer.Context, param: click.Parameter, incomplete : str) -> List[str]:
    
    mgr : ServerManager = ctx.obj["server_mgr"]
    servers = mgr.list_servers()
    return [ s for s in servers if s.startswith(incomplete) ]
    
@server_app.command("connect")
def server_connect(
    ctx : typer.Context,
    server_name : str = typer.Argument(shell_complete=complete_server_name)
):
    mgr : ServerManager = ctx.obj["server_mgr"]
    
    if not mgr.server_name_exists(server_name):
        typer.echo("error: Unknown server. Do 'server list' to show registered servers.")
    else:
        mgr.selected_server = server_name
        
def prompt_optional(label: str, *, hide: bool = False):
    def _cb(ctx: click.Context, param: click.Parameter, value: Optional[str]):
        # Don't prompt during shell completion / help rendering
        if ctx.resilient_parsing:
            return value
        if value is not None:
            return value
        # Prompt once; empty -> None
        ans = typer.prompt(label, default="", show_default=False, hide_input=hide)
        return ans if ans.strip() else None
    return _cb
        
@server_app.command("update")
def register(
    ctx : typer.Context,
    name : str = typer.Argument(shell_complete=complete_server_name),
    ip: Optional[str] = typer.Option(
        None, "--ip",
        callback=prompt_optional("    Server IP (Press Enter to keep current value)"),
        help="Server IP",
        show_default=False,
    ),
    secret: Optional[str] = typer.Option(
        None, "--secret",
        callback=prompt_optional("    Secret (Press Enter to keep current value)", hide=True),
        help="Local name / secret",
        show_default=False,
    )
):
    
    mgr : ServerManager = ctx.obj["server_mgr"]
    mgr.register_server(ip, name, secret)
        
@server_app.command("show")
def server_info(
    ctx : typer.Context,
    server_name : str
):
    mgr : ServerManager = ctx.obj["server_mgr"]
    
    if not mgr.server_name_exists(server_name):
        typer.echo("error: Unknown server. Do 'server list' to show registered servers.")
        return
    
    server = mgr.server_info(server_name=server_name)
    typer.echo(f"Name: \t{server.name}")
    typer.echo(f"Ip: \t{server.ip}")
    
@server_app.command("disconnect")
def server_disconnect(
    ctx : typer.Context
):
    mgr : ServerManager = ctx.obj["server_mgr"]
    mgr.selected_server = None