# from hecaton.gpu.utils import *
# from hecaton.gpu.web_client import GPUWebClient
# from hecaton.gpu.docker_manager import DockerManager
# from hecaton.gpu.worker import start_worker

# # Main code (Outside the docker)

# def main():
#     # Outside dockers (in the server)
#     # main =>
#     # - getpass secret if not registered yet (for a specific server)
#     # - try loading existing cache to see if worker is already registered
#     args = parser.parse_args()
#     worker_config : WorkerConfig = load_worker_config(args.ip)
#     # - connect to server (with cached id or no id)
#     gpu_web_client = GPUWebClient(args.ip, worker_config=worker_config)
#     # - DockerManager.sync =>
#     # - Check if local images are the same as online's
#     # - sync docker images
#     gpu_web_client.update_status('INITIALIZING')
#     docker_manager = DockerManager(gpu_web_client)
#     gpu_web_client.update_status('IDLE')
#     # - Download images that doesn't exist
#     # - start worker
#     # worker =>
#     # - Call hecaton server to check if there is a job (cron every 3 sec)
#     # - Keep track of local workers, if one has been running for more that 10min without update, kill it
#     # - Pickup job (update job status to running)
#     # - start associated imag e (if not already started) with shared as a folder with the name of the image on it
#     # - put the job payload in a file in the shared folder
#     # - check the folder every 3 seconds
#     # - if folder contain output, upload output to server if status is completed (The output is a json file with the status) (allow workers to update with custom statuses)
#     start_worker(gpu_web_client, docker_manager)

# if __name__ == "__main__":
    
#     main()
import typer
import subprocess
import os
import sys
from pathlib import Path
from hecaton.gpu.utils import *
from hecaton.gpu.web_client import GPUWebClient
from hecaton.gpu.docker_manager import DockerManager
from hecaton.gpu.worker import start_worker
from hecaton.gpu.argparser import parser

app = typer.Typer(help="Hecaton GPU Worker Service Manager")

# Service configuration
SERVICE_NAME = "hecaton-gpu"
SERVICE_FILE = f"/etc/systemd/system/{SERVICE_NAME}.service"

def is_service_installed() -> bool:
    """Check if the systemd service is installed"""
    return os.path.exists(SERVICE_FILE)

def is_service_running() -> bool:
    """Check if the service is currently running"""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", SERVICE_NAME],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def get_service_status() -> str:
    """Get the current service status"""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", SERVICE_NAME],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() if result.returncode == 0 else "inactive"
    except (subprocess.SubprocessError, FileNotFoundError):
        return "not-installed"

def ensure_config_exists(ip: str) -> bool:
    """Ensure the worker config exists before installing service"""
    try:
        from hecaton.gpu.utils import load_worker_config
        
        # Try to load config - this will prompt for password if needed
        typer.echo("🔐 Setting up authentication for the service...")
        config = load_worker_config(ip)
        
        if config and config.secret:
            typer.echo("✅ Authentication configured successfully!")
            return True
        else:
            typer.echo("❌ Failed to configure authentication.")
            return False
            
    except Exception as e:
        typer.echo(f"❌ Error configuring authentication: {e}")
        return False

def generate_service_file(ip: str) -> str:
    """Generate the systemd service file content"""
    python_path = sys.executable
    script_path = os.path.abspath(__file__)
    
    service_content = f"""[Unit]
Description=Hecaton GPU Worker Service
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
ExecStart={python_path} {script_path} run --ip {ip}
WorkingDirectory={os.path.dirname(script_path)}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
    return service_content

def run_sudo_command(cmd, success_message, error_message):
    """Run a command with sudo and handle errors"""
    try:
        # Use sudo -A to use the SUDO_ASKPASS mechanism if available
        env = os.environ.copy()
        if 'SUDO_ASKPASS' not in env:
            # If no askpass is set, we'll try direct sudo (will prompt if needed)
            full_cmd = ['sudo'] + cmd
        else:
            full_cmd = ['sudo', '-A'] + cmd
            
        result = subprocess.run(full_cmd, check=True, text=True)
        typer.echo(success_message)
        return True
    except subprocess.CalledProcessError:
        typer.echo(error_message)
        return False
    except FileNotFoundError:
        typer.echo("❌ 'sudo' command not found. Please run as root or install sudo.")
        return False

@app.command()
def install(
    ip: str = typer.Argument(..., help="Server IP address"),
    skip_auth: bool = typer.Option(False, "--skip-auth", help="Skip authentication setup (use if already configured)")
):
    """Install the Hecaton GPU Worker as a system service"""
    if is_service_installed():
        typer.echo("⚠️  Service is already installed.")
        if typer.confirm("Do you want to reinstall?"):
            # Stop and remove existing service first
            if is_service_running():
                run_sudo_command(
                    ["systemctl", "stop", SERVICE_NAME],
                    "✅ Service stopped.",
                    "❌ Failed to stop existing service."
                )
            
            run_sudo_command(
                ["systemctl", "disable", SERVICE_NAME],
                "✅ Service disabled.",
                "⚠️  Could not disable service (may not be enabled)."
            )
            
            run_sudo_command(
                ["rm", "-f", SERVICE_FILE],
                "✅ Old service file removed.",
                "❌ Failed to remove old service file."
            )
        else:
            return
    
    # Ensure authentication is configured before installing service
    if not skip_auth:
        typer.echo("📋 Setting up authentication for the service...")
        if not ensure_config_exists(ip):
            typer.echo("❌ Authentication setup failed. Service installation aborted.")
            raise typer.Exit(code=1)
    else:
        typer.echo("⚠️  Skipping authentication setup. Make sure credentials are already configured.")
    
    # Generate and install service file
    service_content = generate_service_file(ip)
    
    typer.echo("📋 Installing service...")
    
    # Create service file with sudo
    try:
        # Use tee to write the file with sudo
        tee_process = subprocess.Popen(
            ['sudo', 'tee', SERVICE_FILE],
            stdin=subprocess.PIPE,
            text=True
        )
        tee_process.communicate(input=service_content)
        
        if tee_process.returncode != 0:
            typer.echo("❌ Failed to create service file.")
            return
        
        typer.echo("✅ Service file created.")
        
    except Exception as e:
        typer.echo(f"❌ Failed to create service file: {e}")
        return
    
    # Reload systemd
    if not run_sudo_command(
        ["systemctl", "daemon-reload"],
        "✅ Systemd reloaded.",
        "❌ Failed to reload systemd."
    ):
        return
    
    # Enable service
    if not run_sudo_command(
        ["systemctl", "enable", SERVICE_NAME],
        "✅ Service enabled to start on boot.",
        "❌ Failed to enable service."
    ):
        return
    
    typer.echo("🎉 Service installed successfully!")
    typer.echo(f"📋 You can start it with: sudo hecaton-gpu start")
    typer.echo(f"📋 Or check status with: hecaton-gpu status")

@app.command()
def auth(ip: str = typer.Argument(..., help="Server IP address")):
    """Configure authentication for a server (without installing service)"""
    typer.echo("🔐 Setting up authentication...")
    if ensure_config_exists(ip):
        typer.echo("✅ Authentication configured successfully!")
    else:
        typer.echo("❌ Authentication setup failed.")
        raise typer.Exit(code=1)

@app.command()
def uninstall():
    """Uninstall the Hecaton GPU Worker service"""
    if not is_service_installed():
        typer.echo("⚠️  Service is not installed.")
        return
    
    typer.echo("📋 Uninstalling service...")
    
    # Stop service
    if is_service_running():
        if not run_sudo_command(
            ["systemctl", "stop", SERVICE_NAME],
            "✅ Service stopped.",
            "❌ Failed to stop service."
        ):
            typer.echo("⚠️  Continuing with uninstall anyway...")
    
    # Disable service
    if not run_sudo_command(
        ["systemctl", "disable", SERVICE_NAME],
        "✅ Service disabled.",
        "⚠️  Could not disable service (may not be enabled)."
    ):
        typer.echo("⚠️  Continuing with uninstall anyway...")
    
    # Remove service file
    if not run_sudo_command(
        ["rm", "-f", SERVICE_FILE],
        "✅ Service file removed.",
        "❌ Failed to remove service file."
    ):
        return
    
    # Reload systemd
    if not run_sudo_command(
        ["systemctl", "daemon-reload"],
        "✅ Systemd reloaded.",
        "⚠️  Failed to reload systemd (non-critical)."
    ):
        typer.echo("⚠️  Systemd reload failed, but service is uninstalled.")
    
    typer.echo("🎉 Service uninstalled successfully!")

@app.command()
def start():
    """Start the Hecaton GPU Worker service"""
    if not is_service_installed():
        typer.echo("❌ Service is not installed. Please run 'install' command first.")
        raise typer.Exit(code=1)
    
    if is_service_running():
        typer.echo("⚠️  Service is already running.")
        return
    
    if run_sudo_command(
        ["systemctl", "start", SERVICE_NAME],
        "✅ Service started successfully!",
        "❌ Failed to start service. Check logs with: sudo journalctl -u hecaton-gpu"
    ):
        status()

@app.command()
def stop():
    """Stop the Hecaton GPU Worker service"""
    if not is_service_installed():
        typer.echo("⚠️  Service is not installed.")
        return
    
    if not is_service_running():
        typer.echo("⚠️  Service is not running.")
        return
    
    run_sudo_command(
        ["systemctl", "stop", SERVICE_NAME],
        "✅ Service stopped successfully!",
        "❌ Failed to stop service."
    )

@app.command()
def restart():
    """Restart the Hecaton GPU Worker service"""
    if not is_service_installed():
        typer.echo("❌ Service is not installed. Please run 'install' command first.")
        raise typer.Exit(code=1)
    
    if run_sudo_command(
        ["systemctl", "restart", SERVICE_NAME],
        "✅ Service restarted successfully!",
        "❌ Failed to restart service. Check logs with: sudo journalctl -u hecaton-gpu"
    ):
        status()

@app.command()
def status():
    """Check the status of the Hecaton GPU Worker service"""
    if not is_service_installed():
        typer.echo("📋 Status: Not installed")
        typer.echo("\nTo install, run: hecaton-gpu install <server_ip>")
        return
    
    service_status = get_service_status()
    
    if service_status == "active":
        typer.echo("📋 Status: 🟢 Running")
        
        # Show recent logs
        typer.echo("\n📋 Recent logs (last 5 lines):")
        try:
            result = subprocess.run(
                ["journalctl", "-u", SERVICE_NAME, "-n", "5", "--no-pager"],
                capture_output=True,
                text=True
            )
            if result.stdout:
                typer.echo(result.stdout)
            else:
                typer.echo("No logs available.")
        except:
            typer.echo("Could not retrieve logs.")
            
    elif service_status == "inactive":
        typer.echo("📋 Status: 🔴 Stopped")
        typer.echo(f"\nTo start: sudo hecaton-gpu start")
    elif service_status == "failed":
        typer.echo("📋 Status: ❌ Failed")
        typer.echo(f"\nCheck logs with: sudo journalctl -u {SERVICE_NAME} -f")
    else:
        typer.echo(f"📋 Status: {service_status}")

@app.command()
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    lines: int = typer.Option(10, "--lines", "-n", help="Number of lines to show")
):
    """Show service logs"""
    if not is_service_installed():
        typer.echo("❌ Service is not installed.")
        return
    
    try:
        cmd = ["journalctl", "-u", SERVICE_NAME, f"-n{lines}"]
        if follow:
            cmd.append("-f")
        
        # Try without sudo first, then with sudo if needed
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            typer.echo(result.stdout)
        else:
            # Try with sudo
            sudo_cmd = ["sudo"] + cmd
            subprocess.run(sudo_cmd)
    except Exception as e:
        typer.echo(f"❌ Failed to show logs: {e}")

@app.command()
def run(ip: str = typer.Argument(..., help="Server IP address")):
    """Run the worker directly (for service use)"""
    # This is the actual worker logic that the service will run
    typer.echo(f"🚀 Starting Hecaton GPU Worker for server: {ip}")
    
    try:
        # Your original main logic here
        worker_config: WorkerConfig = load_worker_config(ip)
        gpu_web_client = GPUWebClient(ip, worker_config=worker_config)
        gpu_web_client.update_status('INITIALIZING')
        docker_manager = DockerManager(gpu_web_client)
        gpu_web_client.update_status('IDLE')
        start_worker(gpu_web_client, docker_manager)
    except KeyboardInterrupt:
        typer.echo("👋 Service stopped by user")
    except Exception as e:
        typer.echo(f"❌ Service error: {e}")
        sys.exit(1)

def main():
    """Main entry point for the CLI"""
    app()

if __name__ == "__main__":
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        app(["--help"])
    else:
        app()