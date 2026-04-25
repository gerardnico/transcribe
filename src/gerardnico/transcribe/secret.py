import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)


def _get_secret_from_pass(secret_key: str) -> str | None:
    # noinspection PyDeprecation
    pass_path = shutil.which("pass")
    if not pass_path:
        # noinspection PyDeprecation
        pass_path = shutil.which("pass.bat")
    if not pass_path:
        logger.debug(
            f"Unable to find the pass executable. "
            "Container will run without pass variable."
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
        raise ValueError(f"pass returned empty value for {secret_key}")
    return value


def get_secret(env_name: str, pass_name:str) -> str | None:
    env_value = os.getenv(env_name, "").strip()
    if env_value:
        return env_value
    return _get_secret_from_pass(pass_name) or None
