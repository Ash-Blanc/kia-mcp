import logging
import subprocess
import os
import json
import requests
import time
import ast
from pathlib import Path
from functools import lru_cache
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from cocoindex import FlowBuilder, Parser
    from leann import LeannBuilder, LeannSearcher
    import tree_sitter_python as tspython
    LIBRARIES_AVAILABLE = True
except ImportError as e:
    LIBRARIES_AVAILABLE = False
    logger.warning(f"Libraries not available: {e}. Install as per README.")

instructions = """This server provides tools to enhance context for coding agents/IDEs. Key tools include:
- kia_package_search_grep: Perform regex searches in packages (local or remote registries like py_pi, npm).
- kia_package_search_hybrid: Conduct semantic searches in packages using LEANN or remote research.
- kia_package_search_read_file: Read specific sections of package files (local or remote).
- index_repository: Clone and index GitHub repositories for semantic search.
- search_codebase: Query indexed repositories for relevant code snippets.
- visualize_codebase: Generate import graphs for repositories.
- index_documentation: Index web documentation for search.
- search_documentation: Query indexed documentation.
- list_resources: List all indexed resources.
- check_resource_status: Check the status of a specific resource.
- rename_resource: Rename an indexed resource.
- delete_resource: Remove an indexed resource.
- kia_web_search: Perform web searches via Parallel.ai.
- kia_deep_research_agent: Conduct deep research tasks via Parallel.ai.
- initialize_project: Set up MCP configurations for projects.
- read_source_content: Read content from indexed sources.
- kia_context_share: Share context across agents.
- kia_bug_report: Submit bug reports or feedback by opening a GitHub issue.
"""

mcp = FastMCP("kia-mcp", instructions=instructions)

# Globals
searchers = {}
package_searchers = {}
resources = {}
RESOURCES_FILE = Path('/tmp/resources.json')

def save_resources():
    RESOURCES_FILE.parent.mkdir(exist_ok=True)
    with RESOURCES_FILE.open('w') as f:
        json.dump(resources, f)

def load_resources():
    global resources
    if RESOURCES_FILE.exists():
        with RESOURCES_FILE.open('r') as f:
            resources = json.load(f)

load_resources()

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Chunk text into smaller pieces with overlap."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            # Find a good break point (sentence end)
            for i in range(end, max(start, end - 200), -1):
                if text[i] in '.!?\n':
                    end = i + 1
                    break
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end - overlap
    return chunks

def chunk_code_with_tree_sitter(code: str) -> list[str]:
    """Chunk Python code using Tree Sitter for AST-based splitting."""
    try:
        from tree_sitter import Parser
        parser = Parser()
        parser.set_language(tspython.language)
        tree = parser.parse(bytes(code, 'utf-8'))
        chunks = []

        def extract_chunks(node):
            if node.type in ['function_definition', 'class_definition']:
                start = node.start_byte
                end = node.end_byte
                chunk = code[start:end]
                if len(chunk) > 50:
                    chunks.append(chunk)
                return
            for child in node.children:
                extract_chunks(child)

        extract_chunks(tree.root_node)
        if not chunks:
            return chunk_text(code)
        return chunks
    except Exception as e:
        logger.warning(f"Tree Sitter parsing failed: {e}, falling back to text chunking")
        return chunk_text(code)



# Package Search Tools (local and remote)
@mcp.tool()
@lru_cache(maxsize=256)
def kia_package_search_grep(registry: str, package_name: str, pattern: str, version: str = None, output_mode: str = "content") -> str:
    logger.info(f"Grep search in package: {package_name} from {registry}")
    if registry == "local":
        import site
        site_packages = Path(site.getsitepackages()[0])
        package_path = site_packages / package_name
        if package_path.exists():
            result = subprocess.run(['rg', pattern, str(package_path)], capture_output=True, text=True)
            logger.info(f"Grep found matches: {bool(result.stdout)}")
            return result.stdout
        return "Package not installed locally"
    else:
        # Remote search using web search
        query = f"{registry} {package_name} {pattern} code example"
        web_results = kia_web_search(query, num_results=5)
        return f"Remote search results for {pattern} in {package_name}:\n{web_results}"

@mcp.tool()
def kia_package_search_hybrid(registry: str, package_name: str, semantic_queries: list, pattern: str = None, version: str = None) -> str:
    logger.info(f"Hybrid search in package: {package_name} from {registry}")
    if registry == "local":
        if not LIBRARIES_AVAILABLE:
            return "Libraries not available."
        if package_name in package_searchers:
            searcher = package_searchers[package_name]
        else:
            import site
            site_packages = Path(site.getsitepackages()[0])
            package_path = site_packages / package_name
            if not package_path.exists():
                return "Package not installed locally"
            # Collect .py files
            files = list(package_path.rglob('*.py'))[:100]  # limit
            # Index with LEANN
            index_path = Path(f"/tmp/leann_pkg_{package_name}")
            try:
                builder = LeannBuilder(str(index_path))
                for file in files:
                    try:
                        content = file.read_text()
                        chunks = chunk_code_with_tree_sitter(content)
                        for chunk in chunks:
                            builder.add_document(chunk)
                    except Exception as e:
                        logger.warning(f"Error reading {file}: {e}")
                builder.build()
                searcher = LeannSearcher(str(index_path))
                package_searchers[package_name] = searcher
            except Exception as e:
                logger.error(f"Error building package index for {package_name}: {e}")
                return f"Error building index: {e}"
        results = []
        for query in semantic_queries:
            result = searcher.search(query)
            results.append(str(result))
        logger.info(f"Hybrid search completed for {package_name}")
        return '\n'.join(results)
    else:
        # Remote semantic search using deep research
        query = f"Semantic search in {registry} package {package_name}: {'; '.join(semantic_queries)}"
        research_results = kia_deep_research_agent(query)
        return f"Remote hybrid search results for {package_name}:\n{research_results}"

@mcp.tool()
def kia_package_search_read_file(registry: str, package_name: str, filename: str, start_line: int, end_line: int) -> str:
    logger.info(f"Reading file in package: {package_name}/{filename} from {registry}")
    if registry == "local":
        import site
        site_packages = Path(site.getsitepackages()[0])
        file_path = site_packages / package_name / filename
        if file_path.exists():
            lines = file_path.read_text().splitlines()
            if start_line > len(lines) or end_line < start_line:
                return "Invalid line range"
            return '\n'.join(lines[start_line-1:end_line])
        return "File not found"
    else:
        # Remote read using web search
        query = f"{registry} {package_name} {filename} source code"
        web_results = kia_web_search(query, num_results=3)
        return f"Remote file content for {filename} in {package_name}:\n{web_results}"

# Repository Management
@mcp.tool()
def index_repository(repo_url: str, branch: str = "main") -> str:
    logger.info(f"Indexing repository: {repo_url}")
    if not LIBRARIES_AVAILABLE:
        logger.error("Libraries not available")
        return "Libraries not available. Install cocoindex and leann."
    repo_name = repo_url.split('/')[-1].replace('.git', '')
    path = Path(f"/tmp/{repo_name}")
    if path.exists():
        logger.info(f"Repository {repo_name} already exists")
        return f"Repository {repo_name} already cloned."
    result = subprocess.run(["git", "clone", repo_url, str(path), "--branch", branch], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"Git clone failed: {result.stderr}")
        return f"Git clone failed: {result.stderr}"
    # Use cocoindex with Tree Sitter for parsing
    python_parser = Parser.from_tree_sitter(
        language=tspython.language,
        captures={
            "function": ["function_definition"],
            "class": ["class_definition"],
        },
    )
    flow = FlowBuilder()
    flow.add_source("files", str(path))
    flow.parse("python", python_parser)
    flow.transform("merge_chunks", lambda chunks: "\n".join(chunk["content"] for chunk in chunks) if isinstance(chunks, list) else str(chunks))
    chunks = flow.collect()
    # Build LEANN index
    index_path = Path(f"/tmp/leann_{repo_name}")
    try:
        builder = LeannBuilder(str(index_path))
        for chunk in chunks:
            content = chunk.get("content", str(chunk))
            if content.strip():
                builder.add_document(content)
        builder.build()
        searchers[repo_name] = LeannSearcher(str(index_path))
        resources[repo_name] = {'type': 'repository', 'path': str(path), 'status': 'indexed'}
        save_resources()
        logger.info(f"Indexed {repo_name}")
        return f"Indexed {repo_name}"
    except Exception as e:
        logger.error(f"Error building index for {repo_name}: {e}")
        return f"Error building index: {e}"

@mcp.tool()
def search_codebase(query: str, repositories: list, include_sources: bool = True) -> str:
    logger.info(f"Searching codebase: {query} in {repositories}")
    if not query.strip():
        return "Query cannot be empty."
    if not repositories:
        return "No repositories specified."
    results = []
    for repo in repositories:
        if repo in searchers:
            try:
                result = searchers[repo].search(query)
                results.append(f"{repo}: {result}")
            except Exception as e:
                logger.error(f"Error searching {repo}: {e}")
                results.append(f"{repo}: Error {e}")
        else:
            results.append(f"{repo}: Not indexed")
    return '\n'.join(results)

@mcp.tool()
def visualize_codebase(repository: str) -> str:
    logger.info(f"Visualizing codebase: {repository}")
    if repository not in resources or resources[repository]['type'] != 'repository':
        return "Repository not indexed"
    path = Path(resources[repository]['path'])
    G = {}
    for file_path in path.rglob('*.py'):
        rel_path = file_path.relative_to(path)
        G[str(rel_path)] = set()
        try:
            tree = ast.parse(file_path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        G[str(rel_path)].add(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    G[str(rel_path)].add(node.module)
        except Exception as e:
            G[str(rel_path)].add(f"Error parsing: {e}")
    return f"Import graph: {dict(G)}"

# Documentation Management
@mcp.tool()
def index_documentation(url: str, url_patterns: list = None, exclude_patterns: list = None, only_main_content: bool = True) -> str:
    logger.info(f"Indexing documentation: {url}")
    if not LIBRARIES_AVAILABLE:
        return "Libraries not available."
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        content = response.text
        # Improved chunking
        chunks = chunk_text(content)
        doc_name = url.split('/')[-1] or 'doc'
        index_path = Path(f"/tmp/leann_{doc_name}")
        try:
            builder = LeannBuilder(str(index_path))
            for chunk in chunks:
                builder.add_document(chunk)
            builder.build()
            searchers[doc_name] = LeannSearcher(str(index_path))
            resources[doc_name] = {'type': 'documentation', 'url': url, 'status': 'indexed'}
            save_resources()
            logger.info(f"Indexed {doc_name}")
            return f"Indexed {doc_name}"
        except Exception as e:
            logger.error(f"Error building index for {doc_name}: {e}")
            return f"Error building index: {e}"
    except Exception as e:
        logger.error(f"Error indexing {url}: {e}")
        return f"Error indexing {url}: {e}"

@mcp.tool()
def search_documentation(query: str, sources: list, include_sources: bool = True) -> str:
    logger.info(f"Searching documentation: {query} in {sources}")
    if not query.strip():
        return "Query cannot be empty."
    if not sources:
        return "No sources specified."
    results = []
    for source in sources:
        if source in searchers:
            try:
                result = searchers[source].search(query)
                results.append(f"{source}: {result}")
            except Exception as e:
                logger.error(f"Error searching {source}: {e}")
                results.append(f"{source}: Error {e}")
        else:
            results.append(f"{source}: Not indexed")
    return '\n'.join(results)

# Unified Resource Management
@mcp.tool()
def list_resources(resource_type: str = None) -> str:
    logger.info(f"Listing resources: {resource_type}")
    if resource_type:
        filtered = {k: v for k, v in resources.items() if v['type'] == resource_type}
        return str(filtered)
    return str(resources)

@mcp.tool()
def check_resource_status(identifier: str) -> str:
    if identifier in resources:
        return resources[identifier]['status']
    return "Not found"

@mcp.tool()
def rename_resource(identifier: str, new_name: str) -> str:
    if identifier in resources:
        resources[new_name] = resources.pop(identifier)
        save_resources()
        return f"Renamed to {new_name}"
    return "Not found"

@mcp.tool()
def delete_resource(identifier: str) -> str:
    if identifier in resources:
        del resources[identifier]
        if identifier in searchers:
            del searchers[identifier]
        if identifier in package_searchers:
            del package_searchers[identifier]
        save_resources()
        return f"Deleted {identifier}"
    return "Not found"

# Web Search & Research (using Parallel.ai)
@mcp.tool()
@lru_cache(maxsize=128)
def kia_web_search(query: str, num_results: int = 5, category: str = None, days_back: int = None) -> str:
    logger.info(f"Web search: {query}")
    parallel_key = os.getenv("PARALLEL_API_KEY")
    if not parallel_key:
        logger.error("PARALLEL_API_KEY not set")
        return "PARALLEL_API_KEY not set"
    url = "https://api.parallel.ai/v1beta/search"
    headers = {"x-api-key": parallel_key, "Content-Type": "application/json"}
    data = {"objective": query, "max_results": min(num_results, 10)}
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        results = response.json().get("results", [])
        logger.info(f"Found {len(results)} results")
        formatted = []
        for r in results:
            formatted.append(f"Title: {r.get('title', 'N/A')}\nURL: {r.get('url', 'N/A')}\nExcerpts: {'; '.join(r.get('excerpts', [])[:3])}\n")
        return '\n'.join(formatted)
    except Exception as e:
        logger.error(f"Web search error: {e}")
        return f"Error: {e}"

@mcp.tool()
def kia_deep_research_agent(query: str, output_format: str = None) -> str:
    logger.info(f"Deep research: {query}")
    parallel_key = os.getenv("PARALLEL_API_KEY")
    if not parallel_key:
        logger.error("PARALLEL_API_KEY not set")
        return "PARALLEL_API_KEY not set"
    url = "https://api.parallel.ai/v1/tasks/runs"
    headers = {"x-api-key": parallel_key, "Content-Type": "application/json"}
    data = {
        "input": query,
        "processor": "base",
        "task_spec": {"output_schema": "Detailed research summary"}
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        run_id = response.json()["run_id"]
        logger.info(f"Started task {run_id}")
        result_url = f"https://api.parallel.ai/v1/tasks/runs/{run_id}/result"
        for i in range(30):  # wait up to 60s
            res = requests.get(result_url, headers=headers, timeout=10)
            if res.status_code == 200:
                output = res.json().get("output", {}).get("content", "")
                logger.info(f"Task {run_id} completed")
                return str(output)
            time.sleep(2)
        logger.warning(f"Task {run_id} still processing")
        return f"Task {run_id} still processing"
    except Exception as e:
        logger.error(f"Deep research error: {e}")
        return f"Error: {e}"

# Development Tools
@mcp.tool()
def initialize_project(project_root: str, profiles: list = None) -> str:
    logger.info(f"Initializing project: {project_root}")
    config = {
        "mcpServers": {
            "kia": {
                "command": "python",
                "args": ["server.py"],
                "env": {}
            }
        }
    }
    project_path = Path(project_root)
    if profiles:
        for profile in profiles:
            if profile == "cursor":
                config_path = project_path / ".cursor" / "mcp.json"
            elif profile == "vscode":
                config_path = project_path / ".vscode" / "mcp.json"
            else:
                continue
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with config_path.open('w') as f:
                json.dump(config, f)
    return f"Initialized project at {project_root}"

@mcp.tool()
@lru_cache(maxsize=64)
def read_source_content(source_identifier: str) -> str:
    logger.info(f"Reading source: {source_identifier}")
    if source_identifier in resources:
        path_str = resources[source_identifier].get('path') or resources[source_identifier].get('url')
        path = Path(path_str)
        if path.is_file():
            try:
                return path.read_text()
            except Exception as e:
                return f"Error reading file: {e}"
        return f"Content from {path_str}"
    return "Not found"

@mcp.tool()
def kia_context_share(agent_name: str) -> str:
    logger.info(f"Sharing context with agent: {agent_name}")
    # Simple sharing: export resources to a JSON file for the agent
    share_file = Path(f"/tmp/kia_context_{agent_name}.json")
    with share_file.open('w') as f:
        json.dump(resources, f)
    return f"Context shared to {share_file}"

@mcp.tool()
def kia_bug_report(description: str, bug_type: str = "bug", additional_context: str = None) -> str:
    logger.info(f"Bug report: {description}")
    if not description.strip() or len(description) < 10 or len(description) > 5000:
        return "Description must be 10-5000 characters."
    if bug_type not in ["bug", "feature-request", "improvement", "other"]:
        return "Invalid bug_type. Use 'bug', 'feature-request', 'improvement', or 'other'."
    
    title = f"[{bug_type.upper()}] {description[:50]}..."
    body = f"**Type:** {bug_type}\n\n**Description:** {description}\n\n**Additional Context:** {additional_context or 'None'}"
    
    # Check if gh is installed
    try:
        result = subprocess.run(['gh', '--version'], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            logger.error("GitHub CLI not installed")
            return "GitHub CLI not installed. Please install it to submit issues."
    except Exception as e:
        logger.error(f"Error checking gh: {e}")
        return "Error checking GitHub CLI."
    
    # Create issue using gh api
    data = {
        "title": title,
        "body": body,
        "labels": [bug_type]
    }
    try:
        cmd = ['gh', 'api', 'repos/Ash-Blanc/mcp-codebase-server/issues', '--method', 'POST', '--input', '-']
        result = subprocess.run(cmd, input=json.dumps(data), text=True, capture_output=True, timeout=30)
        if result.returncode == 0:
            response = json.loads(result.stdout)
            issue_url = response.get('html_url', 'N/A')
            logger.info(f"Issue created: {issue_url}")
            return f"Bug report submitted as GitHub issue: {issue_url}"
        else:
            logger.error(f"Failed to create issue: {result.stderr}")
            return f"Failed to create issue: {result.stderr}"
    except Exception as e:
        logger.error(f"Error creating issue: {e}")
        return f"Error creating issue: {e}"



@mcp.resource("server://status")
def get_server_status() -> str:
    logger.info("Getting server status")
    return f"Indexed resources: {len(resources)}, Libraries available: {LIBRARIES_AVAILABLE}"

def main():
    mcp.run()

if __name__ == "__main__":
    main()