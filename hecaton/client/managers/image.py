import typer
import os
import click
from typing import Optional, List, Tuple
from hecaton.client.managers.api import HecatonServer
from hecaton.client.managers.server import ServerManager, ServerInfo

image_app = typer.Typer()

class ImageManager:
    
    def list_images(
        self,
        ip,
        secret
    ):
        return HecatonServer.list_images(ip, secret)
    
    def new_image(
        self,
        ip,
        secret,
        image
    ):
        return HecatonServer.new_image(ip, secret, image)
    
    def update_image(
        self,
        ip,
        secret,
        image : str,
        env : List[Tuple[str, str]] | None = None,
        description : Optional[str] = None
    ):
        return HecatonServer.update_image(ip, secret, image, env, description)
        
    
@image_app.command("list")
def list_image(
    ctx : typer.Context
):
    mgr : ImageManager = ctx.obj["image_mgr"]
    server_mgr : ServerManager = ctx.obj["server_mgr"]
    server_info : ServerInfo = server_mgr.connected_server()
    
    images = mgr.list_images(server_info.ip, server_info.secret)
    for image in images:
        typer.echo(image[1])
    
@image_app.command("new")
def new_image(
    ctx : typer.Context,
    image : str
):
    mgr : ImageManager = ctx.obj["image_mgr"]
    server_mgr : ServerManager = ctx.obj["server_mgr"]
    server_info : ServerInfo = server_mgr.connected_server()
    
    typer.echo(mgr.new_image(server_info.ip, server_info.secret, image))


def complete_image_name(ctx : typer.Context, param: click.Parameter, incomplete : str) -> List[str]:
    
    mgr : ImageManager = ctx.obj["image_mgr"]
    server_mgr : ServerManager = ctx.obj["server_mgr"]
    server_info : ServerInfo = server_mgr.connected_server()
    
    images = mgr.list_images(server_info.ip, server_info.secret)
    return [image[1] for image in images if image[1].startswith(incomplete)]

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

@image_app.command("update")
def update_image(
    ctx : typer.Context,
    image : str = typer.Argument(..., shell_complete=complete_image_name),
    env_file_path : Optional[str] = typer.Option(
        None,
        "--fp",
        callback=prompt_optional("    New_env_path (Press Enter to keep current variables)"),
        help="Env Path",
        show_default=False,
    ),
    description : Optional[str] = typer.Option(
        None,
        "--desc",
        callback=prompt_optional("    Description (Press Enter to keep current value)"),
        help="Description",
        show_default=False,
    )
):
    mgr : ImageManager = ctx.obj["image_mgr"]
    server_mgr : ServerManager = ctx.obj["server_mgr"]
    server_info : ServerInfo = server_mgr.connected_server()
    
    env = None
    if env_file_path and not os.path.isfile(env_file_path):
        typer.echo(f"error: Invalid filepath {env_file_path}")
        return
    elif os.path.isfile(env_file_path):
        env = [line.split("=") for line in open(env_file_path, "r").read().split() if "=" in line]
    
    typer.echo(mgr.update_image(server_info.ip, server_info.secret, image, env, description))

@image_app.command("show")
def image_info(
    ctx : typer.Context,
    image : str = typer.Argument(..., shell_complete=complete_image_name)
):
    mgr : ImageManager = ctx.obj["image_mgr"]
    server_mgr : ServerManager = ctx.obj["server_mgr"]
    server_info : ServerInfo = server_mgr.connected_server()
    
    images = mgr.list_images(server_info.ip, server_info.secret)
    for im in images:
        if im[1] == image:
            typer.echo(f'name: \t\t {im[1]}')
            typer.echo(f'description: \t\t {im[2] or "No Description yet..."}')
            typer.echo(f'env: \t\t {im[3]}')