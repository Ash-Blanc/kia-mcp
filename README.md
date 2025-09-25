# Kia MCP Server

A powerful, local MCP server built with FastMCP, cocoindex, LEANN, and Parallel.ai. Provides context augmentation for coding agents/IDEs with repository indexing, documentation search, package exploration, and web research capabilities. Tech stack agnostic, supporting any programming language and framework.

Tell your coding agent: "Use kia_package_search_grep to find how error handling is implemented in the `requests` Python library" or "Search the numpy package for array manipulation examples".

Try indexing public documentation or a repository:
- "Index [https://docs.python.org/3/]"
- "Index [https://github.com/browser-use/browser-use]"
- "Use kia_deep_research_agent to compare the best GraphRAG frameworks and then index the one with least latency."

Check your indexed resources:
- "List my resources" or "Check the status of my indexing jobs"
- Visit your local setup to see all your indexed content.

Improves agent performance by up to 27% through semantic search and Tree Sitter-powered chunking.

## Features

- **Repository Indexing**: Clone and index GitHub repos using cocoindex with Tree Sitter for AST-based chunking and LEANN for semantic search.
- **Documentation Search**: Index and query web documentation.
- **Package Exploration**: Search local or remote packages (PyPI, NPM, etc.) with grep, semantic queries, and file reading.
- **Web Research**: Perform web searches and deep research using Parallel.ai APIs.
- **Codebase Visualization**: Generate import graphs and share context across agents.
- **IDE Integration**: Effortless setup with Cursor, VS Code, Claude Code, and more.
- **Performance**: Improves coding agent productivity by up to 27% through efficient semantic search and local indexing.
- **Free & Open-Source**: No subscription required, enhanced privacy with local processing.

## Quick Setup

### Prerequisites

- Python 3.9+
- uv (Python package manager)
- Rust toolchain (for cocoindex)
- ripgrep (for package search)
- GitHub CLI (gh) for bug reporting (optional, install via `sudo apt install gh` on Linux)
- Parallel.ai API key

### Installation

1. **Install prerequisites**:
    - uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
    - Rust: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh` (source ~/.cargo/env)
    - ripgrep: `sudo apt install ripgrep` (Ubuntu/Debian) or `brew install ripgrep` (macOS)

2. **Install the server**:
    ```bash
    git clone https://github.com/your-repo/kia-mcp-server.git
    cd kia-mcp-server
    uv sync
    ```

   Or as a one-liner (after installing prerequisites):
   ```bash
   git clone https://github.com/your-repo/kia-mcp-server.git && cd kia-mcp-server && uv sync
   ```

5. **Get API key**:
    - Sign up at [Parallel.ai](https://platform.parallel.ai) and set `export PARALLEL_API_KEY="your_key"`

## Running the Server

```bash
uv run kia-mcp-server
```

Or directly:
```bash
uv run python server.py
```

For development, use FastMCP CLI:
```bash
uv run fastmcp run server.py:mcp
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
    "kia": {
      "command": "uv",
      "args": ["run", "kia-mcp-server"],
      "cwd": "/path/to/kia-mcp-server",
      "env": {
        "PARALLEL_API_KEY": "your_key"
      }
    }
  }
}
```

## Usage Examples

### Package Search (No indexing required!)
```
Use package search to find how error handling is implemented in the `requests` Python library: kia_package_search_grep("py_pi", "requests", "error handling")
Search the numpy package for array manipulation examples: kia_package_search_hybrid("py_pi", "numpy", ["array manipulation"])
Read specific file sections: kia_package_search_read_file("py_pi", "requests", "requests.py", 1, 50)
```

### Index Documentation or a Repository
```
Index public documentation: index_documentation("https://docs.python.org/3/")
Index a GitHub repository: index_repository("https://github.com/browser-use/browser-use")
Use deep research to compare frameworks: kia_deep_research_agent("Compare best GraphRAG frameworks and index the one with least latency")
```

### Monitor Progress & Explore
```
List your resources: list_resources()
Check the status of your indexing jobs: check_resource_status("repository", "browser-use")
```

### Demo: Analyze a Framework
```python
async def demo_kia_agent():
    """
    Demo: Analyze a popular framework and find best practices.
    """
    agent, client = await create_code_assistant()

    # Create a session
    response = await client.agents.complete(
        agent=agent,
        messages=[{
            "role": "user",
            "content": """I'm building a React app with authentication. 
            Please:
            1. Index the NextAuth.js repository
            2. Search for JWT implementation patterns
            3. Find documentation about session management
            4. Show me similar auth patterns from other popular repos"""
        }]
    )

    print(response.messages[-1].content)
```

### Submit Bug Report
```
Report an issue: kia_bug_report("Indexing fails for large repos", "bug", "Error: timeout after 10 minutes")
```

## Available Tools

- **kia_package_search_grep**: Regex search in packages (local or remote registries)
- **kia_package_search_hybrid**: Semantic search in packages (local or remote)
- **kia_package_search_read_file**: Read package file sections (local or remote)
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
- **kia_context_share**: Share context across agents
- **kia_bug_report**: Submit bug reports or feedback by opening a GitHub issue

## Resources

- **server://status**: Server status and library availability

## Notes

- Indexes stored in `/tmp` (temporary)
- Requires cocoindex, LEANN, and Tree Sitter for full functionality
- Parallel.ai and Google AI APIs have rate limits
- For production, deploy with FastMCP Cloud

## Troubleshooting

- **Libraries not available**: Run `uv sync` to install dependencies (ensure Rust for cocoindex and Tree Sitter parsers)
- **API key errors**: Check PARALLEL_API_KEY is set
- **Indexing fails**: Verify git, network access, and API quotas
- **IDE not connecting**: Restart IDE after adding server

For issues, check logs or contact support.