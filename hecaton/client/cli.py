import shlex, typer, os
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import ANSI
from hecaton.client.managers import ServerManager, ImageManager, JobManager, apps
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.completion import Completer, Completion
from typer.main import get_command
from typing import Iterable, List, Tuple, Optional
import click
import importlib

app = typer.Typer()

_original_echo = typer.echo

def _indented_echo(message="", indent=4, **kwargs):
    prefix = " " * indent
    msg = "\n".join(prefix + line for line in str(message).splitlines())
    _original_echo(msg, **kwargs)


shared_context = {
    "server_mgr"    : ServerManager(),
    "job_mgr"       : JobManager(),
    "image_mgr"     : ImageManager()
}
def _split_args(text: str):
    try:
        return click.parser.split_arg_string(text)
    except Exception:
        return text.split()

def _resolve_chain(root_cmd, root_ctx, args):
    cmd, ctx, rest = root_cmd, root_ctx, list(args)
    while isinstance(cmd, click.MultiCommand) and rest:
        name, sub_cmd, rest2 = cmd.resolve_command(ctx, rest)
        if not sub_cmd:
            break
        ctx = sub_cmd.make_context(
            info_name=name,
            args=rest2,
            parent=ctx,
            resilient_parsing=True,
            obj=ctx.obj,
        )
        cmd, rest = sub_cmd, rest[1:]
    return cmd, ctx, rest

def _match_option(token: str, options: List[click.Option]) -> Optional[click.Option]:
    for opt in options:
        if token in opt.opts or token in opt.secondary_opts:
            return opt
    return None

def _consume_tokens_for_option(opt: click.Option, tokens: List[str], i: int) -> int:
    
    t = tokens[i]
    
    if "=" in t and t.startswith("-"):
        return i + 1
    
    if opt.nargs == 0:
        return i + 1
    
    return min(i + 1 + opt.nargs, len(tokens))

def determine_active_param(
    leaf_cmd: click.Command,
    args_after_leaf: List[str],
    completing_option_name: bool,
) -> Tuple[str, Optional[click.Parameter], int]:
    """
    Returns (kind, param, pos_index)
      kind ∈ {"option_name", "option_value", "positional", "none"}
      param: the active click.Option or click.Argument (or None)
      pos_index: index of active positional (or -1)
    """
    params = leaf_cmd.params
    opt_params = [p for p in params if isinstance(p, click.Option)]
    pos_params = [p for p in params if isinstance(p, click.Argument)]

    if completing_option_name:
        return ("option_name", None, -1)

    i = 0
    pos_i = 0
    while i < len(args_after_leaf):
        tok = args_after_leaf[i]
        # Option with attached value: --opt=value → treat as fully consumed
        if tok.startswith("--") and "=" in tok:
            i += 1
            continue
        # Option name?
        opt = _match_option(tok, opt_params) if tok.startswith("-") else None
        if opt is not None:
            i = _consume_tokens_for_option(opt, args_after_leaf, i)
            continue
        # Otherwise this token belongs to current positional
        if pos_i < len(pos_params):
            arg = pos_params[pos_i]
            # default nargs is 1; Typer uses 1 unless you set it
            nargs = getattr(arg, "nargs", 1)
            if nargs in (1, None):
                pos_i += 1
                i += 1
            elif nargs == -1:  # variadic: all remaining go here
                # Since we’re *before* the incomplete token, all remaining are consumed
                # and we remain on this positional
                i = len(args_after_leaf)
            else:  # fixed >1
                # consume up to nargs tokens into this positional
                take = min(nargs, len(args_after_leaf) - i)
                pos_i += 1
                i += take
        else:
            # extra tokens; move on
            i += 1

    if args_after_leaf:
        last = args_after_leaf[-1]
        last_opt = _match_option(last, opt_params)
        if last_opt is not None and last_opt.nargs != 0:
            return ("option_value", last_opt, -1)

    if pos_i < len(pos_params):
        return ("positional", pos_params[pos_i], pos_i)

    return ("none", None, -1)

class TyperCompleter(Completer):
    def __init__(self, typer_app, make_root_ctx):
        self.root_cmd = get_command(typer_app)
        self.make_root_ctx = make_root_ctx

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        args = _split_args(text)
        incomplete = "" if text.endswith((" ", "\t")) else (args.pop() if args else "")


        root_ctx = self.make_root_ctx()
        leaf_cmd, leaf_ctx, rest = _resolve_chain(self.root_cmd, root_ctx, args)

        args_after_leaf = rest
        # IMPORTANT: call on the LEAF command with (ctx, incomplete)
        items = list(leaf_cmd.shell_complete(leaf_ctx, incomplete))

        if not items:
            # Decide what we’re completing
            kind, param, pos_index = determine_active_param(
                leaf_cmd,
                args_after_leaf=args_after_leaf,
                completing_option_name=incomplete.startswith("-"),
            )

            if kind == "option_name":
                # suggest option switches
                for p in (pp for pp in leaf_cmd.params if isinstance(pp, click.Option)):
                    for sw in (*p.opts, *p.secondary_opts):
                        if sw.startswith(incomplete):
                            items.append(click.shell_completion.CompletionItem(sw))

            elif kind == "option_value" and param is not None:
                # OPTION value completion → param or its type
                if getattr(param, "shell_complete", None):
                    items = list(param.shell_complete(leaf_ctx, incomplete))
                elif getattr(param.type, "shell_complete", None):
                    items = list(param.type.shell_complete(leaf_ctx, param, incomplete))

            elif kind == "positional" and param is not None:
                # POSITIONAL completion → param or its type
                if getattr(param, "shell_complete", None):
                    items = list(param.shell_complete(leaf_ctx, incomplete))
                elif getattr(param.type, "shell_complete", None):
                    items = list(param.type.shell_complete(leaf_ctx, param, incomplete))

        # yield items
        start = -len(incomplete)
        for it in items:
            yield Completion(it.value, start_position=start,
                            display=it.value, display_meta=(it.help or ""))

@app.callback()
def main(ctx: typer.Context):
    ctx.obj = shared_context

app.add_typer(apps.job_app, name="job")
app.add_typer(apps.image_app, name="image")
app.add_typer(apps.server_app, name="server")
app.add_typer(apps.user_app, name="user")
app.add_typer(apps.worker_app, name="worker")

@app.command("ls")
def list_files():
    print(*["    " + f for f in os.listdir(".")], sep="\n")
    
@app.command("cd")
def change_dir(dir):
    os.chdir(dir)

@app.command("help")
def greet():
    with importlib.resources.open_text("hecaton", "help.txt") as f:
        typer.echo(f.read())

@app.command()
def unknown():
    typer.echo(f"Unknown command")

def run_shell():
    logo = importlib.resources.open_text("hecaton", "logo_hecaton.txt").read()
    # logo = open("logo_hecaton.txt", encoding="utf-8").read()
    typer.echo(logo)

    root_click_cmd = get_command(app)
    def make_root_ctx():
        return root_click_cmd.make_context(
            info_name="", args=[], resilient_parsing=True, obj=shared_context
        )
    completer = TyperCompleter(app, make_root_ctx)
    
    typer.echo = _indented_echo
    session = PromptSession(
        completer=completer,
        complete_while_typing=True
    )
    while True:
        try:
            line = session.prompt(ANSI(f"    \x1b[36;1mhecaton\x1b[0m ({shared_context['server_mgr'].selected_server or 'Not connected'}) \x1b[35m›\x1b[0m "))
        except (EOFError, KeyboardInterrupt):
            break
        if not line.strip(): 
            continue
        if line.strip() in {"quit", "exit"}:
            break
        try:
            # Run Typer/Click without sys.exit()
            app(standalone_mode=False, args=shlex.split(line))
        except SystemExit:
            pass
        except Exception as e:
            typer.echo(f"error: {e}")

def main():
    run_shell()

if __name__ == "__main__":
    main()