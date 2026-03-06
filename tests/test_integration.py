"""
End-to-end integration tests simulating real AI assistant workflows.
"""
import json
import pytest


class TestRealWorldWorkflows:
    """真实场景工作流测试"""

    def test_code_review_workflow(self, sample_file_structure, invoke_tool, run_async):
        """模拟代码审查工作流"""
        # 1. 搜索所有 Python 文件
        search_result = run_async(invoke_tool(
            "search_files",
            path=str(sample_file_structure / "src"),
            pattern="*.py"
        ))
        assert search_result["count"] > 0

        # 2. 读取每个文件内容
        for match in search_result["matches"]:
            read_result = run_async(invoke_tool(
                "read_file",
                path=match["path"]
            ))
            assert "content" in read_result
            # 验证是 Python 代码
            assert "def " in read_result["content"] or "import " in read_result["content"] or "#" in read_result[
                "content"]

    def test_project_documentation_workflow(self, sample_file_structure, invoke_tool, run_async):
        """模拟项目文档工作流"""
        # 1. 列出 docs 目录
        list_result = run_async(invoke_tool(
            "list_directory",
            path=str(sample_file_structure / "docs")
        ))
        assert list_result["count"] == 2

        # 2. 读取 README
        readme_result = run_async(invoke_tool(
            "read_file",
            path=str(sample_file_structure / "docs" / "readme.md")
        ))
        assert "Test Project" in readme_result["content"]

        # 3. 读取配置
        config_result = run_async(invoke_tool(
            "read_file",
            path=str(sample_file_structure / "docs" / "config.json")
        ))
        assert "test" in config_result["content"]

    def test_backup_workflow(self, sample_file_structure, invoke_tool, run_async):
        """模拟备份工作流"""
        src_dir = sample_file_structure / "src"
        backup_dir = sample_file_structure / "backup"

        # 1. 复制整个目录
        copy_result = run_async(invoke_tool(
            "copy_file",
            source=str(src_dir),
            destination=str(backup_dir)
        ))
        assert copy_result.get("success") is True

        # 2. 验证备份完整性
        list_original = run_async(invoke_tool(
            "list_directory",
            path=str(src_dir)
        ))
        list_backup = run_async(invoke_tool(
            "list_directory",
            path=str(backup_dir)
        ))

        assert list_original["count"] == list_backup["count"]

        # 3. 获取文件信息验证
        orig_file = sample_file_structure / "src" / "main.py"
        backup_file = sample_file_structure / "backup" / "main.py"

        info_orig = run_async(invoke_tool("get_file_info", path=str(orig_file)))
        info_backup = run_async(invoke_tool("get_file_info", path=str(backup_file)))

        assert info_orig["md5"] == info_backup["md5"]

    def test_cleanup_workflow(self, sample_file_structure, invoke_tool, run_async):
        """模拟清理临时文件工作流"""
        # 创建一些临时文件
        temp_files = [
            sample_file_structure / "temp1.tmp",
            sample_file_structure / "temp2.tmp",
            sample_file_structure / "docs" / "temp3.tmp"
        ]
        for f in temp_files:
            f.write_text("temp")

        # 搜索所有 .tmp 文件
        search_result = run_async(invoke_tool(
            "search_files",
            path=str(sample_file_structure),
            pattern="*.tmp"
        ))
        assert search_result["count"] == 3

        # 删除每个临时文件
        for match in search_result["matches"]:
            del_result = run_async(invoke_tool(
                "delete_path",
                path=match["path"]
            ))
            assert del_result.get("success") is True

        # 验证清理完成
        verify_search = run_async(invoke_tool(
            "search_files",
            path=str(sample_file_structure),
            pattern="*.tmp"
        ))
        assert verify_search["count"] == 0

    def test_full_project_setup_workflow(self, temp_workspace, invoke_tool, run_async):
        """模拟完整项目初始化工作流"""
        # 1. 创建项目结构
        dirs = ["src", "tests", "docs", "config"]
        for d in dirs:
            result = run_async(invoke_tool(
                "create_directory",
                path=str(temp_workspace / d)
            ))
            assert result.get("success") is True

        # 2. 创建初始文件
        files_content = {
            "README.md": "# New Project\n\nDescription here.",
            "src/main.py": "def main():\n    pass\n\nif __name__ == '__main__':\n    main()",
            "requirements.txt": "fastmcp>=1.0.0\n",
            "config/settings.json": '{"debug": true}'
        }

        for filename, content in files_content.items():
            result = run_async(invoke_tool(
                "write_file",
                path=str(temp_workspace / filename),
                content=content
            ))
            assert result.get("success") is True

        # 3. 验证结构
        root_list = run_async(invoke_tool(
            "list_directory",
            path=str(temp_workspace)
        ))
        assert root_list["count"] == len(dirs) + len(files_content)

        # 4. 搜索所有代码文件
        code_search = run_async(invoke_tool(
            "search_files",
            path=str(temp_workspace),
            pattern="*.py"
        ))
        assert code_search["count"] == 1


class TestMCPProtocolCompliance:
    """MCP 协议合规性测试"""

    def test_tool_registration(self, mcp_tools):
        """测试所有工具已注册"""
        expected_tools = [
            "list_directory",
            "read_file",
            "write_file",
            "create_directory",
            "delete_path",
            "search_files",
            "get_file_info",
            "move_file",
            "copy_file"
        ]

        for tool_name in expected_tools:
            assert tool_name in mcp_tools, f"Tool {tool_name} not registered"

    def test_tool_return_format(self, sample_file_structure, invoke_tool, run_async):
        """测试工具返回格式一致性"""
        # 所有工具应该返回 JSON 字符串
        tools_to_test = [
            ("list_directory", {"path": str(sample_file_structure)}),
            ("get_file_info", {"path": str(sample_file_structure / "secret.txt")}),
            ("read_file", {"path": str(sample_file_structure / "secret.txt")}),
        ]

        for tool_name, kwargs in tools_to_test:
            result = run_async(invoke_tool(tool_name, **kwargs))
            # 验证是有效的 JSON 结构（dict）
            assert isinstance(result, dict)
            # 验证有预期的字段或错误处理
            assert "error" in result or any(k in result for k in ["success", "path", "content", "entries"])