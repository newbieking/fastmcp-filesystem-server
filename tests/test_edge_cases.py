"""
Edge cases and error handling tests.
"""
import json
import pytest
import os


class TestEdgeCases:
    """边界情况测试"""

    def test_very_long_filename(self, temp_workspace, invoke_tool, run_async):
        """测试超长文件名"""
        long_name = "a" * 200 + ".txt"
        long_file = temp_workspace / long_name
        long_file.write_text("content")

        result = run_async(invoke_tool("read_file", path=str(long_file)))

        assert "content" in result or result.get("success") is True

    def test_special_characters_in_filename(self, temp_workspace, invoke_tool, run_async):
        """测试特殊字符文件名"""
        special_names = [
            "file with spaces.txt",
            "file-with-dashes.txt",
            "file_with_underscores.txt",
            "file.multiple.dots.txt",
            "文件中文.txt",
            "🎉emoji.txt"
        ]

        for name in special_names:
            file_path = temp_workspace / name
            file_path.write_text(f"Content of {name}")

            result = run_async(invoke_tool("read_file", path=str(file_path)))
            assert "error" not in result, f"Failed for {name}"

    def test_empty_file(self, temp_workspace, invoke_tool, run_async):
        """测试空文件"""
        empty_file = temp_workspace / "empty.txt"
        empty_file.write_text("")

        result = run_async(invoke_tool("read_file", path=str(empty_file)))

        assert result.get("is_text") is True
        assert result.get("content") == ""
        assert result.get("size") == 0

    def test_large_file_read_limit(self, temp_workspace, invoke_tool, run_async):
        """测试大文件读取限制"""
        large_file = temp_workspace / "large.bin"
        # 创建 1MB 文件
        large_file.write_bytes(b"x" * (1024 * 1024))

        result = run_async(invoke_tool("read_file", path=str(large_file)))

        # 默认应该只读取 100KB
        assert result.get("read_bytes") <= 100 * 1024
        assert result.get("has_more") is True

    def test_binary_file_handling(self, temp_workspace, invoke_tool, run_async):
        """测试二进制文件处理"""
        binary_file = temp_workspace / "binary.dat"
        binary_file.write_bytes(bytes(range(256)))

        result = run_async(invoke_tool("read_file", path=str(binary_file)))

        # 应该识别为二进制
        assert result.get("is_text") is False or "Binary file" in result.get("content", "")

    def test_concurrent_access(self, temp_workspace, invoke_tool, run_async):
        """测试并发访问（简单场景）"""
        import asyncio

        file_path = temp_workspace / "concurrent.txt"
        file_path.write_text("initial")

        async def read_multiple():
            tasks = [
                invoke_tool("read_file", path=str(file_path))
                for _ in range(5)
            ]
            return await asyncio.gather(*tasks)

        results = run_async(read_multiple())

        # 所有读取都应该成功
        assert all("error" not in r for r in results)

    def test_permission_error_handling(self, temp_workspace, invoke_tool, run_async):
        """测试权限错误处理"""
        # 创建无读权限文件（Unix-like 系统）
        restricted_file = temp_workspace / "restricted.txt"
        restricted_file.write_text("secret")

        try:
            os.chmod(str(restricted_file), 0o000)

            result = run_async(invoke_tool("read_file", path=str(restricted_file)))

            # 应该返回错误而不是崩溃
            assert "error" in result or "Permission" in str(result)
        finally:
            # 恢复权限以便清理
            os.chmod(str(restricted_file), 0o644)


class TestPathNormalization:
    """路径规范化测试"""

    def test_relative_path_resolution(self, temp_workspace, invoke_tool, run_async):
        """测试相对路径解析"""
        # 先切换到测试目录
        import os
        original_cwd = os.getcwd()
        os.chdir(temp_workspace)

        try:
            # 使用相对路径
            result = run_async(invoke_tool("list_directory", path="."))
            assert "error" not in result
        finally:
            os.chdir(original_cwd)

    def test_absolute_path(self, temp_workspace, invoke_tool, run_async):
        """测试绝对路径"""
        result = run_async(invoke_tool("list_directory", path=str(temp_workspace)))

        assert "error" not in result
        assert result["path"] == str(temp_workspace)

    def test_path_with_trailing_slash(self, temp_workspace, invoke_tool, run_async):
        """测试尾部斜杠路径"""
        dir_path = temp_workspace / "testdir"
        dir_path.mkdir()

        # 带尾部斜杠
        result = run_async(invoke_tool(
            "list_directory",
            path=str(dir_path) + "/"
        ))

        assert "error" not in result