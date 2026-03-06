"""
File search functionality tests.
"""
import json
import pytest


class TestSearchFiles:
    """文件搜索测试"""

    def test_search_by_name_pattern(self, sample_file_structure, invoke_tool, run_async):
        """测试按文件名通配符搜索"""
        result = run_async(invoke_tool(
            "search_files",
            path=str(sample_file_structure),
            pattern="*.py"
        ))

        assert "error" not in result
        assert result["count"] == 2  # main.py, helper.py

        paths = [m["path"] for m in result["matches"]]
        assert any("main.py" in p for p in paths)
        assert any("helper.py" in p for p in paths)

    def test_search_by_content_pattern(self, sample_file_structure, invoke_tool, run_async):
        """测试按内容正则搜索"""
        result = run_async(invoke_tool(
            "search_files",
            path=str(sample_file_structure),
            pattern="*.py",
            content_pattern="TODO"
        ))

        assert result["count"] >= 1
        # main.py 包含 TODO
        paths = [m["path"] for m in result["matches"]]
        assert any("main.py" in p for p in paths)

    def test_search_markdown_files(self, sample_file_structure, invoke_tool, run_async):
        """测试搜索 Markdown 文件"""
        result = run_async(invoke_tool(
            "search_files",
            path=str(sample_file_structure),
            pattern="*.md"
        ))

        assert result["count"] == 1
        assert "readme.md" in result["matches"][0]["name"]

    def test_search_with_depth_limit(self, sample_file_structure, invoke_tool, run_async):
        """测试深度限制"""
        # 创建深层文件
        deep_dir = sample_file_structure / "level1" / "level2" / "level3"
        deep_dir.mkdir(parents=True)
        (deep_dir / "deep.py").write_text("# deep file")

        # 深度 2 应该找不到
        result_shallow = run_async(invoke_tool(
            "search_files",
            path=str(sample_file_structure),
            pattern="*.py",
            max_depth=2
        ))

        # 深度 5 应该找到
        result_deep = run_async(invoke_tool(
            "search_files",
            path=str(sample_file_structure),
            pattern="*.py",
            max_depth=5
        ))

        assert result_shallow["count"] < result_deep["count"]

    def test_search_no_matches(self, sample_file_structure, invoke_tool, run_async):
        """测试无匹配结果"""
        result = run_async(invoke_tool(
            "search_files",
            path=str(sample_file_structure),
            pattern="*.java"
        ))

        assert result["count"] == 0
        assert result["matches"] == []

    def test_search_content_regex_complex(self, sample_file_structure, invoke_tool, run_async):
        """测试复杂正则内容搜索"""
        result = run_async(invoke_tool(
            "search_files",
            path=str(sample_file_structure),
            pattern="*.py",
            content_pattern="def\s+\w+\(\)"
        ))

        # 应该匹配 def main(): 和 def helper():
        assert result["count"] >= 2