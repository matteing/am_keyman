from rich.console import Console
from rich.progress import Progress
from flask import Flask, request
from jinja2 import Template
import click, configparser, os, jwt, time, requests, webbrowser, threading
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

console = Console()

# Token expiration time must not be greater than 15777000 (6 months in seconds)
EXP_TIME = 15777000

def get_config():
    config_file = configparser.ConfigParser()
    if os.path.exists("./config.ini"):
        config_file.read("./config.ini")
        return config_file
    else:
        console.print(
            "[red]No config file found. Please run `am_keyman configure.`[/red]"
        )
        exit(1)


def validate_config():
    config = get_config()
    if "am_keyman" not in config:
        console.print("[red]No config found. Please run `am_keyman configure`[/red]")
        exit(1)
    if not config.get("am_keyman", "team_id"):
        console.print("[red]No team configured. Please run `am_keyman configure`[/red]")
        exit(1)
    if not config.get("am_keyman", "key_id"):
        console.print("[red]No key configured. Please run `am_keyman configure`[/red]")
        exit(1)
    if not config.get("am_keyman", "key_file"):
        console.print(
            "[red]No key file configured. Please run `am_keyman configure`[/red]"
        )
        exit(1)
    if not os.path.exists(config.get("am_keyman", "key_file")):
        console.print(
            f"[red]Key file not found. Make sure it exists at {config.get('am_keyman', 'key_file')}[/red]"
        )
        exit(1)


@click.group()
def cli():
    pass


@cli.command()
@click.argument("team_id")
@click.argument("key_id")
@click.argument("key_file")
def configure(team_id, key_id, key_file):
    new_config = configparser.ConfigParser()
    new_config["am_keyman"] = {
        "team_id": team_id,
        "key_id": key_id,
        "key_file": key_file,
    }
    with open("./config.ini", "w") as config_file:
        new_config.write(config_file)
    console.print("[green]Saved to config.ini.[/green]")


@cli.command()
def get_dev_token():
    validate_config()
    config = get_config()
    secret = open(config.get("am_keyman", "key_file"), "r").read()
    headers = {"alg": "ES256", "kid": config.get("am_keyman", "key_id")}
    payload = {
        "iss": config.get("am_keyman", "team_id"),
        "exp": int(time.time() + EXP_TIME),
        "iat": time.time(),
    }
    token = jwt.encode(payload, secret, algorithm="ES256", headers=headers)
    with Progress() as progress:
        task = progress.add_task("[cyan]Validating key...", total=None)
        req = requests.get(
            "https://api.music.apple.com/v1/test",
            headers={"Authorization": f"Bearer {token}"},
        )
    if req.status_code == 200:
        progress.update(task, completed=1)
        console.print("[green]Key is valid![/green]")
    else:
        progress.update(task, completed=1)
        console.print("[red]Key is invalid![/red]")
    console.print("[green]Generated token:[/green]")
    print(token)


auth_app = Flask(__name__)

@cli.command()
@click.argument("dev_token")
def get_user_token(dev_token):
    if not dev_token:
        console.print("[red]No dev token provided.[/red]")
        exit(1)
    @auth_app.route('/', methods=['POST', 'GET'])
    def index():
        if request.method == 'POST':
            json = request.get_json()
            if not json['token']:
                return 'Invalid developer token', 403
            else:
                console.print("[green]User token generated![/green]")
                print(json["token"])
                os._exit(0)
        else:
            # Get template from module path
            with open(os.path.join(os.path.dirname(__file__), 'user_auth.html')) as file:
                template = Template(file.read())
                return template.render(developer_token=dev_token)
    def open_browser():
        webbrowser.open("http://127.0.0.1:8000")
    threading.Timer(1, open_browser).start()
    auth_app.run(host='127.0.0.1', port=8000)

if __name__ == "__main__":
    cli()
