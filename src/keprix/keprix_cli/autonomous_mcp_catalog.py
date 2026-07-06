"""
Curated catalog of well-known MCP servers that Keprix can suggest or
auto-spawn. Each entry is a dict with fields understood by MCPServerCreate
and the auto-spawn manager.

Fields:
    key          Stable identifier used as the default server name.
    label        Human-readable display name.
    description  One sentence describing what the server does.
    transport    "stdio" or "http".
    command      Executable for stdio servers (usually "npx").
    args         Argument list for stdio servers.
    url          Base URL for HTTP/SSE servers (template, may be None).
    required_env List of env var names the server needs; empty = no credentials.
    capability_tags  List of lowercase strings describing capabilities. Used by
                     the auto-spawn matcher in prompt 161.
    homepage     Documentation URL shown in the UI (optional).
    auth_type    Optional; ``oauth`` for hosted MCP servers that use OAuth login.
    auto_spawnable   True if the server can be spawned without user credentials.
                     Set to True only for servers where required_env is empty.
"""

from __future__ import annotations

from typing import Any, Dict, List

MCP_CATALOG: List[Dict[str, Any]] = [
    {
        "key": "filesystem",
        "label": "Filesystem",
        "description": "Read and write local files and directories.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem"],
        "required_env": [],
        "capability_tags": ["files", "read", "write", "local"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem",
        "auto_spawnable": True,
    },
    {
        "key": "fetch",
        "label": "Fetch",
        "description": "Fetch web pages and convert them to markdown.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-fetch"],
        "required_env": [],
        "capability_tags": ["web", "http", "fetch", "scrape"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/fetch",
        "auto_spawnable": True,
    },
    {
        "key": "memory",
        "label": "Memory",
        "description": "Persistent entity-based knowledge graph memory.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "required_env": [],
        "capability_tags": ["memory", "entities", "knowledge", "graph"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/memory",
        "auto_spawnable": True,
    },
    {
        "key": "sequential-thinking",
        "label": "Sequential Thinking",
        "description": "Dynamic problem-solving through structured thought sequences.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "required_env": [],
        "capability_tags": ["reasoning", "planning", "thinking", "analysis"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking",
        "auto_spawnable": True,
    },
    {
        "key": "git",
        "label": "Git",
        "description": "Read git history, diffs, and blame across local repositories.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-git"],
        "required_env": [],
        "capability_tags": ["git", "version-control", "code", "history"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/git",
        "auto_spawnable": True,
    },
    {
        "key": "time",
        "label": "Time",
        "description": "Current time and timezone conversion.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-time"],
        "required_env": [],
        "capability_tags": ["time", "date", "timezone", "clock"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/time",
        "auto_spawnable": True,
    },
    {
        "key": "sqlite",
        "label": "SQLite",
        "description": "Query and modify a local SQLite database.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sqlite"],
        "required_env": [],
        "capability_tags": ["database", "sql", "sqlite", "local"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/sqlite",
        "auto_spawnable": True,
    },
    {
        "key": "puppeteer",
        "label": "Puppeteer",
        "description": "Control a headless browser for web automation and screenshots.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "required_env": [],
        "capability_tags": ["browser", "automation", "screenshot", "puppeteer"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/puppeteer",
        "auto_spawnable": True,
    },
    {
        "key": "github",
        "label": "GitHub",
        "description": "Search repos, read files, manage issues and PRs via GitHub API.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "required_env": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
        "capability_tags": ["github", "code", "repos", "issues", "prs"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/github",
        "auto_spawnable": False,
    },
    {
        "key": "brave-search",
        "label": "Brave Search",
        "description": "Web and local search powered by the Brave Search API.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
        "required_env": ["BRAVE_API_KEY"],
        "capability_tags": ["web", "search", "brave"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/brave-search",
        "auto_spawnable": False,
    },
    {
        "key": "postgres",
        "label": "PostgreSQL",
        "description": "Read-only query access to a PostgreSQL database.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres"],
        "required_env": ["POSTGRES_URL"],
        "capability_tags": ["database", "sql", "postgres"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/postgres",
        "auto_spawnable": False,
    },
    {
        "key": "slack",
        "label": "Slack",
        "description": "Read channels and send messages via the Slack API.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-slack"],
        "required_env": ["SLACK_BOT_TOKEN", "SLACK_TEAM_ID"],
        "capability_tags": ["slack", "messaging", "team"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/slack",
        "auto_spawnable": False,
    },
    {
        "key": "notion",
        "label": "Notion",
        "description": "Read and write Notion pages and databases via the official hosted MCP.",
        "transport": "http",
        "url": "https://mcp.notion.com/mcp",
        "required_env": [],
        "auth_type": "oauth",
        "capability_tags": ["notion", "productivity", "notes", "database", "wiki", "pages"],
        "homepage": "https://developers.notion.com/guides/mcp/get-started-with-mcp",
        "auto_spawnable": False,
    },
    {
        "key": "notion-token",
        "label": "Notion (API token)",
        "description": "Notion MCP for automation without OAuth. Share each page with your integration.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@notionhq/notion-mcp-server"],
        "required_env": ["NOTION_TOKEN"],
        "capability_tags": ["notion", "productivity", "notes", "database", "automation", "headless"],
        "homepage": "https://www.notion.so/my-integrations",
        "auto_spawnable": False,
    },
    {
        "key": "trello",
        "label": "Trello",
        "description": "Manage Trello boards, lists, and cards.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@delorenj/mcp-server-trello"],
        "required_env": ["TRELLO_API_KEY", "TRELLO_TOKEN"],
        "capability_tags": ["trello", "kanban", "boards", "cards", "productivity", "project-management"],
        "homepage": "https://github.com/delorenj/mcp-server-trello",
        "auto_spawnable": False,
    },
    {
        "key": "google-maps",
        "label": "Google Maps",
        "description": "Geocoding, directions, and place search via Google Maps.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-google-maps"],
        "required_env": ["GOOGLE_MAPS_API_KEY"],
        "capability_tags": ["maps", "location", "geocoding", "directions"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/google-maps",
        "auto_spawnable": False,
    },
    {
        "key": "everything",
        "label": "Everything (Demo)",
        "description": "Test server exposing all MCP primitives. Use for development only.",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-everything"],
        "required_env": [],
        "capability_tags": ["demo", "test", "development"],
        "homepage": "https://github.com/modelcontextprotocol/servers/tree/main/src/everything",
        "auto_spawnable": True,
    },
]

_CATALOG_BY_KEY: Dict[str, Dict[str, Any]] = {e["key"]: e for e in MCP_CATALOG}


def get_catalog() -> List[Dict[str, Any]]:
    """Return the full catalog list."""
    return MCP_CATALOG


def get_entry(key: str) -> Dict[str, Any]:
    """Return a catalog entry by key, or raise KeyError."""
    entry = _CATALOG_BY_KEY.get(key)
    if not entry:
        raise KeyError(f"Unknown MCP catalog key: {key!r}")
    return entry


def find_by_tags(tags: List[str]) -> List[Dict[str, Any]]:
    """Return catalog entries that match ANY of the given capability tags."""
    tag_set = {t.lower() for t in tags}
    return [
        e
        for e in MCP_CATALOG
        if tag_set.intersection({ct.lower() for ct in e.get("capability_tags", [])})
    ]
