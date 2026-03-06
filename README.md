# FastMCP Filesystem Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-1.0+-green.svg)](https://github.com/jlowin/fastmcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A secure, feature-rich filesystem MCP (Model Context Protocol) server built with [FastMCP](https://github.com/jlowin/fastmcp). Enables AI assistants like Claude to safely read, write, search, and manage files on your local machine with configurable path restrictions.

## Features

- 🔒 **Security First**: Path sandboxing prevents unauthorized directory access
- 📁 **Complete Operations**: List, read, write, create, delete, move, copy files and directories
- 🔍 **Smart Search**: Glob pattern matching with optional content regex search
- 📊 **Metadata**: File hashes (MD5), MIME types, permissions, timestamps
- 🚀 **FastMCP Powered**: Clean decorator-based API, async support, multiple transports
- 🛠️ **Production Ready**: Error handling, logging, size limits, encoding detection

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/newbieking/fastmcp-filesystem-server.git
cd fastmcp-filesystem-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install fastmcp
```

### Usage

#### Standalone Mode

```bash
# Allow access to specific directories only (recommended)
python filesystem_server.py /home/user/Documents /home/user/Projects

# Development mode (no restrictions - use with caution)
python filesystem_server.py
```

#### With Claude Desktop

Add to your Claude Desktop configuration:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "python",
      "args": [
        "/absolute/path/to/filesystem_server.py",
        "/Users/yourname/Documents",
        "/Users/yourname/Projects"
      ]
    }
  }
}
```

**Windows:** `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "python",
      "args": [
        "C:\\path\\to\\filesystem_server.py",
        "C:\\Users\\yourname\\Documents"
      ]
    }
  }
}
```

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `list_directory` | List directory contents | `path` |
| `read_file` | Read file with offset/limit | `path`, `offset`, `limit` |
| `write_file` | Write or append to file | `path`, `content`, `append` |
| `create_directory` | Create directory (mkdir -p) | `path`, `parents` |
| `delete_path` | Delete file or directory | `path`, `recursive` |
| `search_files` | Search by name/content | `path`, `pattern`, `content_pattern`, `max_depth` |
| `get_file_info` | Get metadata + MD5 hash | `path` |
| `move_file` | Move/rename file or directory | `source`, `destination`, `overwrite` |
| `copy_file` | Copy file or directory | `source`, `destination`, `overwrite` |

## Examples

### List Directory
```json
{
  "path": "/home/user/Projects"
}
```

### Read Large File (Chunked)
```json
{
  "path": "/var/log/syslog",
  "offset": 0,
  "limit": 10240
}
```

### Search Python Files Containing "TODO"
```json
{
  "path": "/home/user/Projects",
  "pattern": "*.py",
  "content_pattern": "TODO|FIXME",
  "max_depth": 3
}
```

### Write Configuration File
```json
{
  "path": "/home/user/.config/app/settings.json",
  "content": "{\"theme\": \"dark\", \"version\": \"1.0\"}"
}
```

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Claude/AI     │◄───►│  MCP Protocol    │◄───►│  FastMCP Server │
│   Assistant     │     │  (stdio/SSE)     │     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                              ┌───────────────────────────┼───────────┐
                              ▼                           ▼           ▼
                        ┌──────────┐               ┌────────────┐ ┌────────┐
                        │ Path     │               │ File Ops   │ │ Search │
                        │ Validator│               │ (read/write)│ │ Engine │
                        └──────────┘               └────────────┘ └────────┘
```

## Security Considerations

⚠️ **Important**: This server grants AI assistants direct filesystem access.

1. **Always use path restrictions** in production:
   ```bash
   python filesystem_server.py /safe/path/only
   ```

2. **Never run with sudo/root** permissions

3. **Audit sensitive directories**: Avoid exposing `.ssh/`, `.env files`, or financial data

4. **Review AI actions**: Claude will ask permission before destructive operations (delete/overwrite)

## Development

### Testing

```bash
# Run tests
pytest tests/

# Test with MCP Inspector
npx @modelcontextprotocol/inspector --config mcp-config.json --server fs-server
``` 

### Project Structure

```
.
├── mcp-config.json        # mcp config file for mcp client
├── README.md              # This file
└── fast_mcp_server/
    └── filesystem_server.py  # Main MCP server implementation
```

## Requirements

- Python 3.10+
- `fastmcp>=1.0.0`
- `mcp>=1.0.0`

## License

MIT License - see [LICENSE](LICENSE) file.

## Related

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [Claude Desktop](https://claude.ai/download)

---

**Built with FastMCP** | **Secure by Design** | **AI-Ready**
