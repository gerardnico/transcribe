# Transcribe - Get transcripts from anywhere

* Verb: Do: Transcribe means to convert speech or audio into written text.
* Noun: Done: A transcript is the written text that results from transcribing.

## Install

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

* On Windows, download the latest [vc-redist](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist#latest-supported-redistributable-version)

## Commands

### Get

Get the transcript

```bash
transcribe get uri
transcribe get https://www.tiktok.com/@xxx/video/xxx
# --print-context: show info with doing anything
transcribe --print-context get https://www.tiktok.com/@xxx/video/xxx
```


### Mcp

Start a mcp server

```bash
# stdio server
transcribe mcp
# Streamable http server accessing to the world
transcribe mcp --transport http --host "0.0.0.0"
```

## Conf

### TRANSCRIBE_HOME

`TRANSCRIBE_HOME` is where all data are downloaded/processed.

The default value is `$HOME/.transcribe`. You can see it with the `---print-context` flag before any command.

```powershell
$env:TRANSCRIBE_HOME = "C:\tmp\transcribe"
```

## Mcp Servers

### Stdio Config


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
export  OAUTH_CLIENT_ID="xxxxxxxxxx"
# OAuth client secret
export OAUTH_CLIENT_SECRET="xxxxxxxxx"
# OAuth OOrigin (Authorized JavaScript origins)
export OAUTH_ORIGIN="https://mcp.exampke.com"
# Starting the mcp server
transcribe --verbose mcp --transport http --host "0.0.0.0"
```

## Support

### Whisper - WinError 1114 A dynamic link library (DLL) initialization routine failed.

````
WinError 1114 A dynamic link library (DLL) initialization routine failed.
Error loading "C:\Users\user\code\transcribe\.venv\Lib\site-packages\torch\lib\c10.dll" or one of its dependencies.
````
Download the latest [vc-redist](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist#latest-supported-redistributable-version)


