#!/usr/bin/env python3
"""Build, run and push the Docker image to GitHub Container Registry."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer

DEFAULT_IMAGE = "ghcr.io/gerardnico/transcribe:latest"
CONTAINER_NAME = "transcribe"
APP = typer.Typer(help="Build and release transcribe image to GitHub Container Registry.")
REPO_ROOT = Path(__file__).resolve().parents[1]


def execute_command(command: list[str], cwd: Path) -> None:
    print(f"+ {' '.join(command)}")
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
    )
    if completed.returncode == 0:
        if completed.stdout.strip():
            print(completed.stdout.strip())
        return

    if completed.stdout.strip():
        print(completed.stdout.strip(), file=sys.stderr)
    if completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    raise subprocess.CalledProcessError(
        completed.returncode,
        command,
        output=completed.stdout,
        stderr=completed.stderr,
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
def run() -> None:
    """Run the Docker image only."""
    try:
        image = DEFAULT_IMAGE
        ensure_docker_available()
        execute_command(["docker", "run", "--name", CONTAINER_NAME, "--rm", "-d", "-p", "8000:8000", image],
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
