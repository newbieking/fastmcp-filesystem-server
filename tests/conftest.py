"""
Pytest configuration and shared fixtures for FastMCP Filesystem Server tests.
"""
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# 添加父目录到路径以导入 server
sys.path.insert(0, str(Path(__file__).parent.parent))

from fast_mcp_server.filesystem_server import mcp, set_allowed_paths


@pytest.fixture(scope="function")
def temp_workspace():
    """
    创建临时工作目录，测试后自动清理
    Yields: Path object of temporary directory
    """
    temp_dir = tempfile.mkdtemp(prefix="mcp_test_")
    yield Path(temp_dir)
    # 清理
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def restricted_server(temp_workspace):
    """
    配置受限的 MCP 服务器（安全模式）
    """
    set_allowed_paths([str(temp_workspace)])
    yield temp_workspace
    # 重置为无限制（开发模式）
    set_allowed_paths([])


@pytest.fixture(scope="function")
def sample_file_structure(temp_workspace):
    """
    创建标准测试文件结构：
    temp_workspace/
    ├── docs/
    │   ├── readme.md
    │   └── config.json
    ├── src/
    │   ├── main.py
    │   └── utils/
    │       └── helper.py
    ├── empty_dir/
    └── secret.txt
    """
    # 创建目录
    (temp_workspace / "docs").mkdir()
    (temp_workspace / "src" / "utils").mkdir(parents=True)
    (temp_workspace / "empty_dir").mkdir()

    # 创建文件
    (temp_workspace / "docs" / "readme.md").write_text(
        "# Test Project\n\nThis is a test readme.\nTODO: add more content"
    )
    (temp_workspace / "docs" / "config.json").write_text(
        '{"name": "test", "version": "1.0"}'
    )
    (temp_workspace / "src" / "main.py").write_text(
        "def main():\n    print('Hello World')\n    # TODO: implement\n    pass"
    )
    (temp_workspace / "src" / "utils" / "helper.py").write_text(
        "def helper():\n    return 42"
    )
    (temp_workspace / "secret.txt").write_text("password123\nsecret_key=abc")

    return temp_workspace


@pytest.fixture
def mcp_tools():
    """
    获取 MCP 服务器注册的所有工具
    """
    return mcp._tools


@pytest.fixture
def invoke_tool():
    """
    辅助函数：调用 MCP 工具并解析 JSON 结果
    """
    async def _invoke(tool_name: str, **kwargs):
        tool = mcp._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")

        # FastMCP 工具可能是 sync 或 async
        import inspect
        if inspect.iscoroutinefunction(tool):
            result = await tool(**kwargs)
        else:
            result = tool(**kwargs)

        # 解析 JSON 结果
        import json
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"raw_result": result}

    return _invoke


@pytest.fixture
def run_async():
    """
    在同步测试上下文中运行异步代码
    """
    import asyncio

    def _run(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    return _run