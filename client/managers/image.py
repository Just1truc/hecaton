import typer
import click
from typing import Optional, List
from client.managers.api import HecatonServer
from client.managers.server import ServerManager, ServerInfo

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