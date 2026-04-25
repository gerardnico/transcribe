# Transcribe - Get transcripts from anywhere

* Verb: Do: Transcribe means to convert speech or audio into written text.
* Noun: Done: A transcript is the written text that results from transcribing.

## Install

### From code

* Pipx: Create a venv, install dependency, install script

```bash
# rm -rf ~/.local/share/pipx/venvs/transcribe
pipx install -e --force .
# or
uv tool install
```

Dependency:

* Deno for challenge: https://github.com/yt-dlp/yt-dlp/wiki/EJS

```bash
brew install deno
```

* `ffmpeg` for voice extraction
* whisper for speech to text

* On Windows, download the
  latest [vc-redist](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist#latest-supported-redistributable-version)

### With Docker

You can run it with:

```bash
docker run --rm ghcr.io/gerardnico/transcribe:latest $ARGS
```

## Commands

### Get a transcript

Get a transcript:

```bash
# with the cli
transcribe get https://www.tiktok.com/@xxx/video/xxx
# with docker
docker run --rm ghcr.io/gerardnico/transcribe:latest get https://www.tiktok.com/@xxx/video/xxx
```

For gated content, you can pass the `session-id`

* For TikTok, the `sessionid` cookie value found in the browser

```bash
transcribe get --session-id 57bc2990711e7d14fxxx https://www.tiktok.com/@xxx/video/xxx
```

### Start a Mcp Server

Start a mcp server

#### Mcp Local Stdio server

To start a local stdio server

```bash
# with the cli
transcribe mcp
# with docker
docker run --rm ghcr.io/gerardnico/transcribe:latest mcp
```

#### Mcp Remote Http Server

```bash
# Streamable http server accessing to the world
transcript mcp --transport http
# with docker (host should be 0.0.0.0 and port 8206)
docker run --rm ghcr.io/gerardnico/transcribe:latest mcp --host 0.0.0.0 --port 8206
```

## Conf

### TRANSCRIBE_HOME

`TRANSCRIBE_HOME` is where all data are downloaded/processed.

The default value is `$HOME/.transcribe`. You can see it with the `---print-context` flag before any command.

```powershell
$env:TRANSCRIBE_HOME = "C:\tmp\transcribe"
```

### Mcp Servers Config

Example for a [local stdio server](#mcp-local-stdio-server)

```json
{
  "mcpServers": {
    "transcribe": {
      "command": "transcribe",
      "args": [
        "mcp"
      ]
    }
  }
}
```

### MCP HTTP OAuth2 with Google

You may enable oauth with Google by setting this environment values:

```bash
# OAuth client ID
export OAUTH_CLIENT_ID="xxxxxxxxxx"
# OAuth client secret
export OAUTH_CLIENT_SECRET="xxxxxxxxx"
# OAuth OOrigin (Authorized JavaScript origins)
export OAUTH_ORIGIN="https://mcp.exampke.com"
```

You can then start a [mcp server](#start-a-mcp-server)

## Support / Contributing

See [the dedicated page](CONTRIBUTING.md)