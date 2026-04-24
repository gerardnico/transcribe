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