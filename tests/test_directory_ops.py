"""
Directory operation tests.
"""
import json
import pytest


class TestListDirectory:
    """目录列表测试"""

    def test_list_existing_directory(self, sample_file_structure, invoke_tool, run_async):
        """测试列出目录内容"""
        docs_dir = sample_file_structure / "docs"

        result = run_async(invoke_tool("list_directory", path=str(docs_dir)))

        assert "error" not in result
        assert result["path"] == str(docs_dir)
        assert result["count"] == 2  # readme.md, config.json

        names = [e["name"] for e in result["entries"]]
        assert "readme.md" in names
        assert "config.json" in names

    def test_list_empty_directory(self, sample_file_structure, invoke_tool, run_async):
        """测试空目录"""
        empty_dir = sample_file_structure / "empty_dir"

        result = run_async(invoke_tool("list_directory", path=str(empty_dir)))

        assert result["count"] == 0
        assert result["entries"] == []

    def test_list_nonexistent_directory(self, sample_file_structure, invoke_tool, run_async):
        """测试不存在的目录"""
        fake_dir = sample_file_structure / "not_exist"

        result = run_async(invoke_tool("list_directory", path=str(fake_dir)))

        assert "error" in result

    def test_list_file_as_directory(self, sample_file_structure, invoke_tool, run_async):
        """测试将文件当目录列出"""
        file_path = sample_file_structure / "secret.txt"

        result = run_async(invoke_tool("list_directory", path=str(file_path)))

        assert "error" in result
        assert "not a directory" in result["error"].lower()


class TestCreateDirectory:
    """目录创建测试"""

    def test_create_single_directory(self, sample_file_structure, invoke_tool, run_async):
        """测试创建单层目录"""
        new_dir = sample_file_structure / "new_folder"

        result = run_async(invoke_tool("create_directory", path=str(new_dir)))

        assert result.get("success") is True
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_create_nested_directories(self, sample_file_structure, invoke_tool, run_async):
        """测试递归创建多层目录"""
        deep_dir = sample_file_structure / "a" / "b" / "c" / "d"

        result = run_async(invoke_tool(
            "create_directory",
            path=str(deep_dir),
            parents=True
        ))

        assert result.get("success") is True
        assert deep_dir.exists()

    def test_create_existing_directory(self, sample_file_structure, invoke_tool, run_async):
        """测试创建已存在的目录（幂等性）"""
        existing = sample_file_structure / "docs"

        result = run_async(invoke_tool("create_directory", path=str(existing)))

        # 应该成功（mkdir -p 行为）
        assert result.get("success") is True


class TestDeletePath:
    """删除操作测试"""

    def test_delete_file(self, sample_file_structure, invoke_tool, run_async):
        """测试删除文件"""
        target = sample_file_structure / "secret.txt"
        assert target.exists()

        result = run_async(invoke_tool("delete_path", path=str(target)))

        assert result.get("success") is True
        assert not target.exists()

    def test_delete_empty_directory(self, sample_file_structure, invoke_tool, run_async):
        """测试删除空目录"""
        target = sample_file_structure / "empty_dir"

        result = run_async(invoke_tool("delete_path", path=str(target)))

        assert result.get("success") is True
        assert not target.exists()

    def test_delete_non_empty_directory_without_recursive(self, sample_file_structure, invoke_tool, run_async):
        """测试非递归删除非空目录（应该失败）"""
        target = sample_file_structure / "docs"

        result = run_async(invoke_tool(
            "delete_path",
            path=str(target),
            recursive=False
        ))

        assert "error" in result
        assert "not empty" in result["error"].lower() or "recursive" in result["error"].lower()
        assert target.exists()  # 确保未删除

    def test_delete_non_empty_directory_with_recursive(self, sample_file_structure, invoke_tool, run_async):
        """测试递归删除非空目录"""
        target = sample_file_structure / "src"

        result = run_async(invoke_tool(
            "delete_path",
            path=str(target),
            recursive=True
        ))

        assert result.get("success") is True
        assert not target.exists()

    def test_delete_nonexistent_path(self, sample_file_structure, invoke_tool, run_async):
        """测试删除不存在的路径"""
        fake_path = sample_file_structure / "ghost"

        result = run_async(invoke_tool("delete_path", path=str(fake_path)))

        assert "error" in result
        assert "does not exist" in result["error"].lower()