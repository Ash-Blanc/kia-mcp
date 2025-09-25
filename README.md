# Alternative Nia Context MCP Server

A powerful, local alternative to Nia Context MCP server, built with FastMCP, cocoindex, LEANN, and Parallel.ai. Provides context augmentation for coding agents/IDEs with repository indexing, documentation search, package exploration, and web research capabilities.

## Features

- **Repository Indexing**: Clone and index GitHub repos using cocoindex and LEANN for semantic search.
- **Documentation Search**: Index and query web documentation.
- **Package Exploration**: Search installed Python packages with grep and semantic queries.
- **Web Research**: Perform web searches and deep research using Parallel.ai APIs.
- **IDE Integration**: Effortless setup with Cursor, VS Code, Claude Code, and more.

## Quick Setup

### Prerequisites

- Python 3.9+
- Rust toolchain (for cocoindex)
- uv (for LEANN)
- ripgrep (for package search)
- Parallel.ai API key

### Installation

1. **Install Rust**:
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   source ~/.cargo/env
   pip install maturin
   ```

2. **Install uv**:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install ripgrep**:
   ```bash
   # Ubuntu/Debian
   sudo apt install ripgrep
   # macOS
   brew install ripgrep
   ```

4. **Install libraries**:
   ```bash
   pip install git+https://github.com/cocoindex-io/cocoindex.git
   uv venv && source .venv/bin/activate && uv pip install leann
   pip install -r requirements.txt
   ```

5. **Get API key**:
   - Sign up at [Parallel.ai](https://platform.parallel.ai)
   - Set environment variable: `export PARALLEL_API_KEY="your_key"`

## Running the Server

```bash
python server.py
```

For development, use FastMCP CLI:
```bash
fastmcp run server.py:mcp
```

## IDE Integration

### Cursor

1. Install FastMCP CLI: `pip install fastmcp`
2. Add to Cursor: `fastmcp install cursor`
3. Restart Cursor. The server will auto-connect.

### VS Code

1. Install FastMCP CLI: `pip install fastmcp`
2. Add to VS Code: `fastmcp install vscode`
3. Reload VS Code window.

### Claude Code

1. Install FastMCP CLI: `pip install fastmcp`
2. Add to Claude Code: `fastmcp install claude_code`
3. Restart Claude Code.

### Claude Desktop

1. Install FastMCP CLI: `pip install fastmcp`
2. Add to Claude Desktop: `fastmcp install claude_desktop`
3. Restart Claude Desktop.

### Manual Configuration

For other clients, add to MCP config:

```json
{
  "mcpServers": {
    "alt-nia": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "PARALLEL_API_KEY": "your_key"
      }
    }
  }
}
```

## Usage Examples

### Index a Repository
```
Index the FastAPI repo: index_repository("https://github.com/tiangolo/fastapi")
```

### Search Codebase
```
Find error handling in FastAPI: search_codebase("error handling", ["fastapi"])
```

### Web Search
```
Search for Python async best practices: kia_web_search("Python async best practices")
```

### Deep Research
```
Research GraphRAG frameworks: kia_deep_research_agent("Compare best GraphRAG frameworks")
```

### Package Search
```
Grep for 'import' in requests: kia_package_search_grep("requests", "import")
```

## Available Tools

- **kia_package_search_grep**: Regex search in installed packages
- **kia_package_search_hybrid**: Semantic search in packages
- **kia_package_search_read_file**: Read package file sections
- **index_repository**: Index GitHub repositories
- **search_codebase**: Semantic search in indexed repos
- **visualize_codebase**: Generate import graph
- **index_documentation**: Index web docs
- **search_documentation**: Query indexed docs
- **list_resources**: List indexed resources
- **check_resource_status**: Check indexing status
- **rename_resource**: Rename resources
- **delete_resource**: Remove resources
- **kia_web_search**: Web search via Parallel.ai
- **kia_deep_research_agent**: Deep research via Parallel.ai
- **initialize_project**: Setup IDE configs
- **read_source_content**: Read indexed content

## Resources

- **server://status**: Server status and library availability

## Notes

- Indexes stored in `/tmp` (temporary)
- Requires cocoindex and LEANN for full functionality
- Parallel.ai API has rate limits
- For production, deploy with FastMCP Cloud

## Troubleshooting

- **Libraries not available**: Ensure cocoindex and LEANN are installed
- **API key errors**: Check PARALLEL_API_KEY is set
- **Indexing fails**: Verify git and network access
- **IDE not connecting**: Restart IDE after adding server

For issues, check logs or contact support.