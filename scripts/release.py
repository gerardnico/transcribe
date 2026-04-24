#!/usr/bin/env python3
"""Build, run and push the Docker image to GitHub Container Registry."""

from __future__ import annotations

import subprocess
import sys
import shutil
import threading
from pathlib import Path

import typer

DEFAULT_IMAGE = "ghcr.io/gerardnico/transcribe:latest"
CONTAINER_NAME = "transcribe"
APP = typer.Typer(help="Build and release transcribe image to GitHub Container Registry.")
REPO_ROOT = Path(__file__).resolve().parents[1]


def execute_command(command: list[str], cwd: Path) -> None:
    print(f"+ {' '.join(command)}", flush=True)
    process = subprocess.Popen(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    def stream_output(pipe, target_stream, collected: list[str]) -> None:
        assert pipe is not None
        for line in iter(pipe.readline, ""):
            collected.append(line)
            print(line, end="", file=target_stream, flush=True)
        pipe.close()

    stdout_thread = threading.Thread(
        target=stream_output,
        args=(process.stdout, sys.stdout, stdout_lines),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=stream_output,
        args=(process.stderr, sys.stderr, stderr_lines),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    return_code = process.wait()
    stdout_thread.join()
    stderr_thread.join()

    if return_code == 0:
        return

    stdout_text = "".join(stdout_lines)
    stderr_text = "".join(stderr_lines)
    raise subprocess.CalledProcessError(
        return_code,
        command,
        output=stdout_text,
        stderr=stderr_text,
    )


def ensure_docker_available() -> None:
    try:
        subprocess.run(["docker", "version"], check=True, capture_output=True, text=True)
    except Exception as error:
        raise RuntimeError(
            "Docker was not found"
        ) from error


def fail_runtime(error: Exception) -> None:
    typer.echo(str(error), err=True)
    raise typer.Exit(code=1)


def build_image(image: str) -> None:
    execute_command(["docker", "build", "-t", image, "."], cwd=REPO_ROOT)


def get_secret_from_pass(secret_key: str) -> str | None:
    # noinspection PyDeprecation
    pass_path = shutil.which("pass")
    if not pass_path:
        # noinspection PyDeprecation
        pass_path = shutil.which("pass.bat")
    if not pass_path:
        typer.echo(
            f"Warning: unable to find the pass executable. "
            "Container will run without pass variable.",
            err=True,
        )
        return None

    result = subprocess.run(
        [pass_path, secret_key],
        check=True,
        capture_output=True,
        text=True,
    )
    value = result.stdout.strip()
    if not value:
        typer.echo(f"Warning: pass returned empty value for {secret_key}", err=True)
        return None
    return value


@APP.command("build")
def build(
    image: str = typer.Option(
        DEFAULT_IMAGE,
        "--image",
        help=f"Target image tag (default: {DEFAULT_IMAGE})",
    ),
) -> None:
    """Build the Docker image only."""
    try:
        typer.echo(f"Starting build")
        ensure_docker_available()
        build_image(image)
        typer.echo(f"Build completed: {image}")
    except Exception as error:
        fail_runtime(error)


@APP.command("run")
def run(no_daemon: bool = typer.Option(
    False,
    "--no-daemon",
    help=f"No Daemon",
), ) -> None:
    """Run the Docker image only."""
    try:
        port = 8206 # same as in the docker image
        image = DEFAULT_IMAGE
        ensure_docker_available()
        run_args = [
            "docker",
            "run",
            "--name",
            CONTAINER_NAME,
            "--rm",
            "-p",
            f"{port}:{port}",
        ]
        oauth_client_id = get_secret_from_pass("transcribe/google/oauth-client-id")
        if oauth_client_id:
            run_args.extend(["-e", f"OAUTH_CLIENT_ID={oauth_client_id}"])
        oauth_client_secret = get_secret_from_pass("transcribe/google/oauth-client-secret")
        if oauth_client_secret:
            run_args.extend(["-e", f"OAUTH_CLIENT_SECRET={oauth_client_secret}"])
        run_args.extend(["-e", f"OAUTH_ORIGIN=http://127.0.0.1:{port}"])
        if not no_daemon:
            run_args.append("-d")
        run_args.extend([image, "mcp", "--transport", "http", "--host", "0.0.0.0", "--port", f"{port}"])
        execute_command(
            run_args,
            cwd=REPO_ROOT)
        typer.echo(f"Container {CONTAINER_NAME} started with the image {image}")
    except Exception as error:
        fail_runtime(error)


@APP.command("stop")
def stop() -> None:
    """Stop the container"""
    try:
        ensure_docker_available()
        execute_command(["docker", "stop", CONTAINER_NAME],
                        cwd=REPO_ROOT)
        typer.echo(f"Container {CONTAINER_NAME} stopped")
    except Exception as error:
        fail_runtime(error)


@APP.command("push")
def push() -> None:
    """Run the Docker image only."""
    try:
        image = DEFAULT_IMAGE
        ensure_docker_available()
        push_image(image)
        typer.echo(f"Image pushed: {image}")
    except Exception as error:
        fail_runtime(error)


def push_image(image):
    execute_command(["docker", "push", image], cwd=REPO_ROOT)


@APP.command("release")
def release(
    image: str = typer.Option(
        DEFAULT_IMAGE,
        "--image",
        help=f"Target image tag (default: {DEFAULT_IMAGE})",
    ),
) -> None:
    """Build and push the Docker image."""
    try:
        ensure_docker_available()
        build_image(image)
        push_image(image)
        typer.echo(f"Release completed: {image}")
    except subprocess.CalledProcessError as error:
        if error.stderr and ("unauthorized" in error.stderr.lower() or "denied" in error.stderr.lower()):
            typer.echo(
                "\nGHCR authentication appears missing or invalid.\n"
                "Log in and retry with:\n"
                "  echo <GITHUB_TOKEN> | docker login ghcr.io -u <github_user> --password-stdin\n"
                "Token should have at least write:packages scope.",
                err=True,
            )
        raise typer.Exit(code=error.returncode if error.returncode else 1)
    except RuntimeError as error:
        fail_runtime(error)


if __name__ == "__main__":
    APP()
