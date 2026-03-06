"""
Security and path validation tests.
"""
import json
import pytest
from pathlib import Path


class TestPathValidation:
    """路径验证和安全沙箱测试"""

    def test_validate_path_within_allowed(self, restricted_server):
        """测试允许路径内的访问"""
        from fast_mcp_server.filesystem_server import _validate_path

        test_file = restricted_server / "test.txt"
        test_file.write_text("content")

        # 应该成功
        result = _validate_path(str(test_file))
        assert result == test_file.resolve()

    def test_validate_path_outside_allowed(self, restricted_server, tmp_path):
        """测试越权路径访问被拒绝"""
        from fast_mcp_server.filesystem_server import _validate_path

        outside_file = tmp_path / "outside.txt"
        outside_file.write_text("secret")

        # 应该抛出 PermissionError
        with pytest.raises(PermissionError):
            _validate_path(str(outside_file))

    def test_path_traversal_attack_blocked(self, restricted_server):
        """测试路径遍历攻击防护"""
        from fast_mcp_server.filesystem_server import _validate_path

        # 尝试通过 ../ 跳出限制目录
        malicious_path = str(restricted_server / ".." / "etc" / "passwd")

        with pytest.raises(PermissionError):
            _validate_path(malicious_path)

    def test_symlink_escape_blocked(self, restricted_server, tmp_path):
        """测试符号链接逃逸防护"""
        from fast_mcp_server.filesystem_server import _validate_path

        # 创建指向外部目录的符号链接
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        (outside_dir / "secret.txt").write_text("secret")

        symlink = restricted_server / "escape_link"
        symlink.symlink_to(outside_dir)

        # 解析后应该检测到越权
        with pytest.raises(PermissionError):
            _validate_path(str(symlink / "secret.txt"))


class TestToolSecurity:
    """工具级别的安全测试"""

    def test_list_directory_outside_allowed(self, restricted_server, tmp_path, invoke_tool, run_async):
        """测试 list_directory 越权拒绝"""
        outside_dir = tmp_path / "private"
        outside_dir.mkdir()

        result = run_async(invoke_tool("list_directory", path=str(outside_dir)))

        assert "error" in result
        assert "Access denied" in result["error"] or "Permission denied" in result["error"]

    def test_read_file_outside_allowed(self, restricted_server, tmp_path, invoke_tool, run_async):
        """测试 read_file 越权拒绝"""
        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("secret")

        result = run_async(invoke_tool("read_file", path=str(outside_file)))

        assert "error" in result

    def test_write_file_outside_allowed(self, restricted_server, tmp_path, invoke_tool, run_async):
        """测试 write_file 越权拒绝"""
        outside_path = tmp_path / "hack.txt"

        result = run_async(invoke_tool(
            "write_file",
            path=str(outside_path),
            content="hacked"
        ))

        assert "error" in result
        assert not outside_path.exists()  # 确保未创建

    def test_delete_protection_outside_allowed(self, restricted_server, tmp_path, invoke_tool, run_async):
        """测试 delete 越权保护"""
        outside_file = tmp_path / "important.txt"
        outside_file.write_text("important data")

        result = run_async(invoke_tool("delete_path", path=str(outside_file)))

        assert "error" in result
        assert outside_file.exists()  # 确保未删除