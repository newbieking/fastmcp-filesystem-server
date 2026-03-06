"""
File read/write/operation tests.
"""
import json
import pytest


class TestReadFile:
    """文件读取测试"""

    def test_read_existing_file(self, sample_file_structure, invoke_tool, run_async):
        """测试读取存在的文件"""
        readme = sample_file_structure / "docs" / "readme.md"

        result = run_async(invoke_tool("read_file", path=str(readme)))

        assert result["success"] is True or "content" in result
        assert "Test Project" in result.get("content", "")
        assert result.get("is_text") is True

    def test_read_nonexistent_file(self, sample_file_structure, invoke_tool, run_async):
        """测试读取不存在的文件"""
        fake_path = sample_file_structure / "not_exist.txt"

        result = run_async(invoke_tool("read_file", path=str(fake_path)))

        assert "error" in result
        assert "not found" in result["error"].lower() or "does not exist" in result["error"].lower()

    def test_read_directory_as_file(self, sample_file_structure, invoke_tool, run_async):
        """测试将目录当文件读取的错误处理"""
        docs_dir = sample_file_structure / "docs"

        result = run_async(invoke_tool("read_file", path=str(docs_dir)))

        assert "error" in result
        assert "directory" in result["error"].lower()

    def test_read_with_offset_and_limit(self, sample_file_structure, invoke_tool, run_async):
        """测试分块读取"""
        main_file = sample_file_structure / "src" / "main.py"

        # 读取前 20 字节
        result = run_async(invoke_tool(
            "read_file",
            path=str(main_file),
            offset=0,
            limit=20
        ))

        assert "content" in result
        assert result["offset"] == 0
        assert result["read_bytes"] <= 20
        assert result.get("has_more") is True

    def test_read_binary_file(self, sample_file_structure, invoke_tool, run_async):
        """测试二进制文件读取（返回 hex 预览）"""
        # 创建一个二进制文件
        binary_file = sample_file_structure / "data.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd\xfc")

        result = run_async(invoke_tool("read_file", path=str(binary_file)))

        assert "is_text" in result
        if not result["is_text"]:
            assert "Binary file" in result["content"] or "hex" in result["content"].lower()


class TestWriteFile:
    """文件写入测试"""

    def test_write_new_file(self, sample_file_structure, invoke_tool, run_async):
        """测试写入新文件"""
        new_file = sample_file_structure / "new_file.txt"

        result = run_async(invoke_tool(
            "write_file",
            path=str(new_file),
            content="Hello, World!"
        ))

        assert result.get("success") is True
        assert new_file.exists()
        assert new_file.read_text() == "Hello, World!"

    def test_write_overwrite_existing(self, sample_file_structure, invoke_tool, run_async):
        """测试覆盖现有文件"""
        existing = sample_file_structure / "secret.txt"
        original_content = existing.read_text()

        result = run_async(invoke_tool(
            "write_file",
            path=str(existing),
            content="New content"
        ))

        assert result.get("success") is True
        assert existing.read_text() == "New content"

    def test_write_append_mode(self, sample_file_structure, invoke_tool, run_async):
        """测试追加模式"""
        existing = sample_file_structure / "secret.txt"
        original = existing.read_text()

        result = run_async(invoke_tool(
            "write_file",
            path=str(existing),
            content="\nAppended line",
            append=True
        ))

        assert result.get("success") is True
        new_content = existing.read_text()
        assert new_content.startswith(original)
        assert "Appended line" in new_content

    def test_write_creates_parent_directories(self, sample_file_structure, invoke_tool, run_async):
        """测试自动创建父目录"""
        deep_file = sample_file_structure / "level1" / "level2" / "level3" / "file.txt"

        result = run_async(invoke_tool(
            "write_file",
            path=str(deep_file),
            content="Deep file"
        ))

        assert result.get("success") is True
        assert deep_file.exists()
        assert deep_file.read_text() == "Deep file"

    def test_write_unicode_content(self, sample_file_structure, invoke_tool, run_async):
        """测试 Unicode 内容写入"""
        unicode_file = sample_file_structure / "unicode.txt"
        unicode_content = "你好世界 🌍 ñoël 日本語"

        result = run_async(invoke_tool(
            "write_file",
            path=str(unicode_file),
            content=unicode_content
        ))

        assert result.get("success") is True
        assert unicode_file.read_text() == unicode_content


class TestFileInfo:
    """文件信息获取测试"""

    def test_get_file_info_existing(self, sample_file_structure, invoke_tool, run_async):
        """测试获取文件元数据"""
        main_py = sample_file_structure / "src" / "main.py"

        result = run_async(invoke_tool("get_file_info", path=str(main_py)))

        assert "error" not in result
        assert result["name"] == "main.py"
        assert result["type"] == "file"
        assert result["size"] > 0
        assert "md5" in result
        assert "mime_type" in result
        assert result.get("is_symlink") is False

    def test_get_directory_info(self, sample_file_structure, invoke_tool, run_async):
        """测试获取目录元数据"""
        src_dir = sample_file_structure / "src"

        result = run_async(invoke_tool("get_file_info", path=str(src_dir)))

        assert result["type"] == "directory"
        assert result["size"] is None  # 目录 size 为 None

    def test_file_info_consistency(self, sample_file_structure, invoke_tool, run_async):
        """测试 MD5 哈希一致性"""
        test_file = sample_file_structure / "hash_test.txt"
        content = "Test content for hashing"
        test_file.write_text(content)

        result1 = run_async(invoke_tool("get_file_info", path=str(test_file)))
        result2 = run_async(invoke_tool("get_file_info", path=str(test_file)))

        assert result1["md5"] == result2["md5"]
        assert len(result1["md5"]) == 32  # MD5 长度


class TestMoveAndCopy:
    """移动和复制测试"""

    def test_move_file(self, sample_file_structure, invoke_tool, run_async):
        """测试移动文件"""
        src = sample_file_structure / "secret.txt"
        dst = sample_file_structure / "moved_secret.txt"

        result = run_async(invoke_tool(
            "move_file",
            source=str(src),
            destination=str(dst)
        ))

        assert result.get("success") is True
        assert not src.exists()
        assert dst.exists()
        assert "password123" in dst.read_text()

    def test_move_directory(self, sample_file_structure, invoke_tool, run_async):
        """测试移动目录"""
        src = sample_file_structure / "docs"
        dst = sample_file_structure / "archived_docs"

        result = run_async(invoke_tool(
            "move_file",
            source=str(src),
            destination=str(dst)
        ))

        assert result.get("success") is True
        assert not src.exists()
        assert (dst / "readme.md").exists()

    def test_copy_file(self, sample_file_structure, invoke_tool, run_async):
        """测试复制文件"""
        src = sample_file_structure / "secret.txt"
        dst = sample_file_structure / "backup_secret.txt"

        result = run_async(invoke_tool(
            "copy_file",
            source=str(src),
            destination=str(dst)
        ))

        assert result.get("success") is True
        assert src.exists()  # 源文件仍在
        assert dst.exists()
        assert src.read_text() == dst.read_text()

    def test_copy_directory_recursive(self, sample_file_structure, invoke_tool, run_async):
        """测试递归复制目录"""
        src = sample_file_structure / "src"
        dst = sample_file_structure / "src_backup"

        result = run_async(invoke_tool(
            "copy_file",
            source=str(src),
            destination=str(dst)
        ))

        assert result.get("success") is True
        assert (dst / "main.py").exists()
        assert (dst / "utils" / "helper.py").exists()

    def test_move_no_overwrite_protection(self, sample_file_structure, invoke_tool, run_async):
        """测试覆盖保护"""
        src = sample_file_structure / "secret.txt"
        dst = sample_file_structure / "docs" / "readme.md"  # 已存在

        result = run_async(invoke_tool(
            "move_file",
            source=str(src),
            destination=str(dst),
            overwrite=False
        ))

        assert "error" in result
        assert "exists" in result["error"].lower()