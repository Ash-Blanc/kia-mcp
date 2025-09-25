import logging
import subprocess
import os
import json
import requests
import time
import ast
from pathlib import Path
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from cocoindex import FlowBuilder
    from leann import LeannBuilder, LeannSearcher
    LIBRARIES_AVAILABLE = True
except ImportError:
    LIBRARIES_AVAILABLE = False
    logger.warning("cocoindex and/or leann not available. Install as per README.")

mcp = FastMCP("alt-nia-mcp-server")

# Globals
searchers = {}
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

# Package Search Tools (local approximations)
@mcp.tool()
def kia_package_search_grep(package_name: str, pattern: str, version: str = None, output_mode: str = "content") -> str:
    logger.info(f"Grep search in package: {package_name}")
    import site
    site_packages = Path(site.getsitepackages()[0])
    package_path = site_packages / package_name
    if package_path.exists():
        result = subprocess.run(['rg', pattern, str(package_path)], capture_output=True, text=True)
        logger.info(f"Grep found matches: {bool(result.stdout)}")
        return result.stdout
    return "Package not installed locally"

@mcp.tool()
def kia_package_search_hybrid(package_name: str, semantic_queries: list, pattern: str = None) -> str:
    logger.info(f"Hybrid search in package: {package_name}")
    if not LIBRARIES_AVAILABLE:
        return "Libraries not available."
    import site
    site_packages = Path(site.getsitepackages()[0])
    package_path = site_packages / package_name
    if package_path.exists():
        # Collect .py files
        files = list(package_path.rglob('*.py'))[:50]  # limit
        # Index with LEANN
        index_path = Path(f"/tmp/leann_pkg_{package_name}")
        builder = LeannBuilder(str(index_path))
        for file in files:
            try:
                content = file.read_text()
                builder.add_document(content)
            except Exception as e:
                logger.warning(f"Error reading {file}: {e}")
        builder.build()
        searcher = LeannSearcher(str(index_path))
        results = []
        for query in semantic_queries:
            result = searcher.search(query)
            results.append(str(result))
        logger.info(f"Hybrid search completed for {package_name}")
        return '\n'.join(results)
    return "Package not installed locally"

@mcp.tool()
def kia_package_search_read_file(package_name: str, filename: str, start_line: int, end_line: int) -> str:
    logger.info(f"Reading file in package: {package_name}/{filename}")
    import site
    site_packages = Path(site.getsitepackages()[0])
    file_path = site_packages / package_name / filename
    if file_path.exists():
        lines = file_path.read_text().splitlines()
        if start_line > len(lines) or end_line < start_line:
            return "Invalid line range"
        return '\n'.join(lines[start_line-1:end_line])
    return "File not found"

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
    # Use cocoindex to process
    flow = FlowBuilder()
    flow.add_source("files", str(path))
    flow.transform("chunk", lambda content: str(content).split('\n\n') if len(str(content)) > 1000 else [str(content)])
    chunks = flow.collect()
    # Build LEANN index
    index_path = Path(f"/tmp/leann_{repo_name}")
    builder = LeannBuilder(str(index_path))
    for chunk in chunks:
        builder.add_document(str(chunk))
    builder.build()
    searchers[repo_name] = LeannSearcher(str(index_path))
    resources[repo_name] = {'type': 'repository', 'path': str(path), 'status': 'indexed'}
    save_resources()
    logger.info(f"Indexed {repo_name}")
    return f"Indexed {repo_name}"

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
        # Simple chunking
        chunks = [c for c in content.split('\n\n') if len(c.strip()) > 50][:1000]  # Filter and limit
        doc_name = url.split('/')[-1] or 'doc'
        index_path = Path(f"/tmp/leann_{doc_name}")
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
        if identifier in indexes:
            del indexes[identifier]
        save_resources()
        return f"Deleted {identifier}"
    return "Not found"

# Web Search & Research (using Parallel.ai)
@mcp.tool()
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
        return str([{"url": r["url"], "title": r["title"], "excerpts": r["excerpts"][:3]} for r in results])
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
        for i in range(60):  # wait up to 60s
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
            "alt-nia": {
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



@mcp.resource("server://status")
def get_server_status() -> str:
    logger.info("Getting server status")
    return f"Indexed resources: {len(resources)}, Libraries available: {LIBRARIES_AVAILABLE}"

if __name__ == "__main__":
    mcp.run()