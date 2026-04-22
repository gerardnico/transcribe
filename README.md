# Transcribe - Get transcripts from anywhere

* Verb: Do: Transcribe means to convert speech or audio into written text.
* Noun: Done: A transcript is the written text that results from transcribing.

## Install

* Pipx: Create a venv, install dependency, install script

```bash
# rm -rf ~/.local/share/pipx/venvs/transcribe
pipx install -e --force .
```

* Deno for challenge: https://github.com/yt-dlp/yt-dlp/wiki/EJS

```bash
brew install deno
```

## Commands

### Get

Get the transcript

```bash
transcribe get uri
transcribe get https://www.tiktok.com/@xxx/video/xxx
```

### Info

Show general information

```bash
transcribe info uri
```

### Mcp

Start a mcp server

```bash
transcribe mcp
```

## Conf

### TRANSCRIBE_HOME

`TRANSCRIBE_HOME` is where all data are downloaded/processed.

The default value is `$HOME/.transcribe`. You can see it with the [info command](#info) before downloading.

```powershell
$env:TRANSCRIBE_HOME = "C:\tmp\transcribe"
```

### Mcp

```json
{
  "mcpServers": {
    "weather": {
      "command": "C:\\Users\\name\\.local\\bin\\uv.exe",
      "args": [
        "--directory",
        "C:\\Users\\name\\code\\transcribe",
        "run",
        "src\\gerardnico\\transcribe\\cli.py",
        "mcp"
      ]
    }
  }
}
```

### MCP HTTP OAuth2 (Google)

When using HTTP transport for MCP, the server requires Google OAuth2 ID tokens and an email allowlist.

Set these environment variables before starting the HTTP MCP server:

```powershell
$env:GOOGLE_CLIENT_ID = "<your-google-oauth-client-id>"
$env:AUTHORIZED_EMAILS = "user1@example.com,user2@example.com"
```

- `GOOGLE_CLIENT_ID`: Google OAuth client ID used to validate incoming bearer ID tokens.
- `AUTHORIZED_EMAILS`: comma-separated list of allowed user emails.