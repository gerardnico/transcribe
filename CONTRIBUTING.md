# Contributing Guideline

We follow this [GitHub contributing guideline](https://docs.github.com/en/contributing)

## Mcp Agent Configuration for local HTTP MCP server

When developing, if you want to test the HTTP MCP server locally, you can use:

Example:

* in Claude: `Menu > Developer > Open App Config file`

```json
{
  "mcpServers": {
    "transcribe": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "http://127.0.0.1:8206/mcp"
      ]
    }
  }
}
```

## Support / Debug

### Get the context information

`--print-context`: show info without doing anything

```bash
transcribe --print-context get https://www.tiktok.com/@xxx/video/xxx
```

### This post may not be comfortable for some audiences. Log in for access

You may get this error:

```
Transcript download error has occurred
TikTok 7613409335158279446
This post may not be comfortable for some audiences. Log in for access.
Use --cookies-from-browser or --cookies for the authentication.
See https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp
for how to manually pass cookies
req_011CaP5B3Xu1sQAZLXSX8RgC
````

We provide a `--session-id` flag in the [get command](README.md#get-a-transcript) to pass easily the session id cookie.

### Whisper - WinError 1114 A dynamic link library (DLL) initialization routine failed.

````
WinError 1114 A dynamic link library (DLL) initialization routine failed.
Error loading "C:\Users\user\code\transcribe\.venv\Lib\site-packages\torch\lib\c10.dll" or one of its dependencies.
````

Download the
latest [vc-redist](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist#latest-supported-redistributable-version)
