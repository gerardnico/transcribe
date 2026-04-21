# Transcribe Utility: Script to get a Transcript

* Verb: Do: Transcribe means to convert speech or audio into written text.
* Noun: Done: A transcript is the written text that results from transcribing.

## How to use / Requirement

### Install

* Pipx: Create a venv, install dependency, install script

```bash
# rm -rf ~/.local/share/pipx/venvs/transcribe
pipx install -e --force .
```

* Deno for challenge: https://github.com/yt-dlp/yt-dlp/wiki/EJS

```bash
brew install deno
```

### Run

```bash
transcribe https://www.tiktok.com/@xxx/video/xxx
```

## Mcp Configuration

```json
{
  "mcpServers": {
    "weather": {
      "command": "C:\\Users\\name\\.local\\bin\\uv.exe",
      "args": [
        "--directory",
        "C:\\Users\\name\\code\\transcribe",
        "run",
        "src\\gerardnico\\transcribe\\mcp\\mcp_server.py"
      ]
    }
  }
}
```

## Conf

* `TRANSCRIBE_HOME` (default to `$HOME/.transcribe`): the runtime path
