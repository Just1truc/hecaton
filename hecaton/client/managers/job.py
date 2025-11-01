import typer, os
import click
from typing import Optional, List
from hecaton.client.managers.api import HecatonServer
from hecaton.client.managers.server import ServerManager, ServerInfo
from hecaton.client.managers.image import complete_image_name
from pathlib import Path

job_app = typer.Typer()

class JobManager:
    
    def list_jobs(
        self,
        ip,
        secret
    ):
        return HecatonServer.list_jobs(ip, secret)
    
    def new_job(
        self,
        ip : str,
        secret : str,
        file : str,
        image : str
    ):
        return HecatonServer.new_job(ip, secret, file, image)   
    
    def show_job(
        self,
        ip : str,
        secret : str,
        jid : str
    ):
        return HecatonServer.get_job(ip, secret, jid)
    
def display_job(job : tuple):
    
    jid, image_name, status, updated_at = job
    
    return f"{jid}\t{image_name}\t\t{status}\t{updated_at}"

@job_app.command("list")
def list_jobs(
    ctx : typer.Context
):
    mgr : JobManager = ctx.obj["job_mgr"]
    server_mgr : ServerManager = ctx.obj["server_mgr"]
    server_info : ServerInfo = server_mgr.server_info(server_mgr.selected_server)
    
    jobs = mgr.list_jobs(server_info.ip, server_info.secret)
    typer.echo("jid\t\t\t\t\t\timage_name\t\t\tstatus\t\tupdated_at")
    for job in jobs:
        typer.echo(display_job(job))
    
def complete_file_path(ctx : typer.Context, param: click.Parameter, incomplete : str) -> List[str]:
    
    p = Path(incomplete or ".")
    base = p.parent if p.name else p
    try:
        return [
            str(child) + ("/" if child.is_dir() else "")
            for child in base.iterdir()
            if child.name.startswith(p.name)
        ]
    except FileNotFoundError:
        return []
    
@job_app.command("new")
def new_job(
    ctx : typer.Context,
    file_path : str = typer.Argument(..., shell_complete=complete_file_path),
    image_name : str = typer.Argument(shell_complete=complete_image_name)
):
    if not os.path.isfile(file_path):
        typer.echo("error: File not found")
        return
    
    mgr : JobManager = ctx.obj["job_mgr"]
    server_mgr : ServerManager = ctx.obj["server_mgr"]
    server_info : ServerInfo = server_mgr.connected_server()
    
    typer.echo(mgr.new_job(server_info.ip, server_info.secret, file_path, image_name))
    
def complete_job_id(ctx : typer.Context, param: click.Parameter, incomplete : str) -> List[str]:
    mgr : JobManager = ctx.obj["job_mgr"]
    server_mgr : ServerManager = ctx.obj["server_mgr"]
    server_info : ServerInfo = server_mgr.server_info(server_mgr.selected_server)
    
    jobs = mgr.list_jobs(server_info.ip, server_info.secret)
    return [ job[0] for job in jobs if job[0].startswith(incomplete) ]
    
@job_app.command("show")
def show_job(
    ctx : typer.Context,
    job_id : str = typer.Argument(..., shell_complete=complete_job_id)
):
    mgr : JobManager = ctx.obj["job_mgr"]
    server_mgr : ServerManager = ctx.obj["server_mgr"]
    server_info : ServerInfo = server_mgr.connected_server()
    
    id, status, payload, index, _ = mgr.show_job(server_info.ip, server_info.secret, job_id)
    
    typer.echo(f"jid: {id}")
    typer.echo(f"status: {status}")
    typer.echo(f"payload: {payload}")
    typer.echo(f"index: {index}")