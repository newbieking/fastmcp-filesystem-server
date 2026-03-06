import hashlib
import json
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from mcp.server import FastMCP

mcp = FastMCP("my-fs-mcp")

# 安全基目录限制（防止越权访问）
ALLOWED_BASE_PATHS: List[str] = []

def set_allowed_paths(paths: List[str]):
    """设置允许访问的基目录（安全沙箱）"""
    global ALLOWED_BASE_PATHS
    ALLOWED_BASE_PATHS = [str(Path(p).resolve()) for p in paths]


def _validate_path(path: str) -> Path:
    """验证并解析路径，确保在安全范围内"""
    resolved = Path(path).resolve()

    if not ALLOWED_BASE_PATHS:
        # 开发模式：允许所有路径（生产环境务必限制）
        return resolved

    # 检查是否在允许的路径内
    for base in ALLOWED_BASE_PATHS:
        try:
            resolved.relative_to(base)
            return resolved
        except ValueError:
            continue

    raise PermissionError(f"Access denied: {path} is outside allowed directories")


def _get_file_info(file_path: Path) -> Dict[str, Any]:
    """获取文件/目录的元数据"""
    stat = file_path.stat()
    mime_type, _ = mimetypes.guess_type(str(file_path))

    return {
        "path": str(file_path),
        "name": file_path.name,
        "type": "directory" if file_path.is_dir() else "file",
        "size": stat.st_size if file_path.is_file() else None,
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "permissions": oct(stat.st_mode)[-3:],
        "mime_type": mime_type,
        "is_symlink": file_path.is_symlink()
    }


# ==================== 工具定义 ====================

@mcp.tool()
def list_directory(path: str = ".") -> str:
    """
    列出目录内容

    Args:
        path: 目标目录路径（相对或绝对）
    """
    try:
        target = _validate_path(path)

        if not target.exists():
            return json.dumps({"error": f"Path does not exist: {path}"}, ensure_ascii=False)

        if not target.is_dir():
            return json.dumps({"error": f"Not a directory: {path}"}, ensure_ascii=False)

        entries = []
        for item in target.iterdir():
            try:
                entries.append(_get_file_info(item))
            except (OSError, PermissionError):
                # 跳过无权限访问的条目
                entries.append({
                    "path": str(item),
                    "name": item.name,
                    "type": "unknown",
                    "error": "Permission denied"
                })

        return json.dumps({
            "path": str(target),
            "entries": entries,
            "count": len(entries)
        }, ensure_ascii=False, indent=2)

    except PermissionError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
def read_file(path: str, offset: int = 0, limit: Optional[int] = None) -> str:
    """
    读取文件内容（支持大文件分块读取）

    Args:
        path: 文件路径
        offset: 起始字节偏移量
        limit: 最大读取字节数（默认无限制，建议文本文件不超过 100KB）
    """
    try:
        target = _validate_path(path)

        if not target.exists():
            return json.dumps({"error": f"File not found: {path}"}, ensure_ascii=False)

        if target.is_dir():
            return json.dumps({"error": f"Path is a directory: {path}"}, ensure_ascii=False)

        file_size = target.stat().st_size

        # 安全限制：默认最多读取 100KB 文本
        if limit is None:
            limit = 100 * 1024

        with open(target, 'rb') as f:
            f.seek(offset)
            content = f.read(limit)

            # 尝试解码为文本
            try:
                text_content = content.decode('utf-8')
                is_text = True
            except UnicodeDecodeError:
                # 二进制文件，返回 base64 或提示
                text_content = content[:200].hex()
                is_text = False

            result = {
                "path": str(target),
                "size": file_size,
                "offset": offset,
                "read_bytes": len(content),
                "is_text": is_text,
                "content": text_content if is_text else f"[Binary file, hex preview: {text_content}...]",
                "has_more": (offset + len(content)) < file_size
            }

            if result["has_more"]:
                result["next_offset"] = offset + len(content)

            return json.dumps(result, ensure_ascii=False, indent=2)

    except PermissionError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Read failed: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
def write_file(path: str, content: str, append: bool = False) -> str:
    """
    写入文件内容

    Args:
        path: 目标文件路径
        content: 要写入的内容
        append: 是否追加模式（默认覆盖）
    """
    try:
        target = _validate_path(path)

        # 确保父目录存在
        target.parent.mkdir(parents=True, exist_ok=True)

        mode = 'a' if append else 'w'
        with open(target, mode, encoding='utf-8') as f:
            f.write(content)

        return json.dumps({
            "success": True,
            "path": str(target),
            "bytes_written": len(content.encode('utf-8')),
            "operation": "append" if append else "write"
        }, ensure_ascii=False)

    except PermissionError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Write failed: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
def create_directory(path: str, parents: bool = True) -> str:
    """
    创建目录

    Args:
        path: 目录路径
        parents: 是否自动创建父目录（类似 mkdir -p）
    """
    try:
        target = _validate_path(path)
        target.mkdir(parents=parents, exist_ok=True)

        return json.dumps({
            "success": True,
            "path": str(target),
            "created": not target.exists()  # 实际是否新创建
        }, ensure_ascii=False)

    except PermissionError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Create directory failed: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
def delete_path(path: str, recursive: bool = False) -> str:
    """
    删除文件或目录（危险操作，默认非递归）

    Args:
        path: 目标路径
        recursive: 是否递归删除目录内容
    """
    try:
        target = _validate_path(path)

        if not target.exists():
            return json.dumps({"error": f"Path does not exist: {path}"}, ensure_ascii=False)

        if target.is_file() or target.is_symlink():
            target.unlink()
            return json.dumps({
                "success": True,
                "deleted": str(target),
                "type": "file"
            }, ensure_ascii=False)

        if target.is_dir():
            if not recursive:
                # 尝试删除空目录
                try:
                    target.rmdir()
                    return json.dumps({
                        "success": True,
                        "deleted": str(target),
                        "type": "empty_directory"
                    }, ensure_ascii=False)
                except OSError:
                    return json.dumps({
                        "error": f"Directory not empty. Use recursive=true to force delete: {path}"
                    }, ensure_ascii=False)
            else:
                # 递归删除
                import shutil
                shutil.rmtree(target)
                return json.dumps({
                    "success": True,
                    "deleted": str(target),
                    "type": "directory_recursive"
                }, ensure_ascii=False)

    except PermissionError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Delete failed: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
def search_files(
        path: str = ".",
        pattern: str = "*",
        content_pattern: Optional[str] = None,
        max_depth: int = 5
) -> str:
    """
    搜索文件（按名称通配符，可选内容匹配）

    Args:
        path: 搜索起始目录
        pattern: 文件名通配符（如 "*.py", "test*"）
        content_pattern: 可选的文件内容正则匹配（仅文本文件）
        max_depth: 最大递归深度
    """
    try:
        import fnmatch
        import re

        base = _validate_path(path)
        if not base.is_dir():
            return json.dumps({"error": f"Not a directory: {path}"}, ensure_ascii=False)

        matches = []
        content_regex = re.compile(content_pattern) if content_pattern else None

        for root, dirs, files in os.walk(base):
            # 控制深度
            current_depth = len(Path(root).relative_to(base).parts)
            if current_depth >= max_depth:
                del dirs[:]  # 停止深入
                continue

            for filename in files:
                if fnmatch.fnmatch(filename, pattern):
                    file_path = Path(root) / filename

                    # 如果需要内容匹配
                    if content_regex:
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                if not content_regex.search(f.read()):
                                    continue
                        except Exception:
                            continue  # 跳过无法读取的文件

                    matches.append(_get_file_info(file_path))

        return json.dumps({
            "search_path": str(base),
            "pattern": pattern,
            "content_pattern": content_pattern,
            "matches": matches,
            "count": len(matches)
        }, ensure_ascii=False, indent=2)

    except PermissionError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Search failed: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
def get_file_info(path: str) -> str:
    """获取文件或目录的详细信息"""
    try:
        target = _validate_path(path)

        if not target.exists():
            return json.dumps({"error": f"Path not found: {path}"}, ensure_ascii=False)

        info = _get_file_info(target)

        # 如果是文件，添加额外信息
        if target.is_file():
            # 计算哈希
            hasher = hashlib.md5()
            try:
                with open(target, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        hasher.update(chunk)
                info["md5"] = hasher.hexdigest()
            except Exception:
                info["md5"] = None

        return json.dumps(info, ensure_ascii=False, indent=2)

    except PermissionError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def move_file(source: str, destination: str, overwrite: bool = False) -> str:
    """
    移动或重命名文件/目录

    Args:
        source: 源路径
        destination: 目标路径
        overwrite: 是否覆盖已存在的目标
    """
    try:
        src = _validate_path(source)
        dst = _validate_path(destination)

        if not src.exists():
            return json.dumps({"error": f"Source not found: {source}"}, ensure_ascii=False)

        if dst.exists() and not overwrite:
            return json.dumps({"error": f"Destination exists (use overwrite=true): {destination}"}, ensure_ascii=False)

        # 确保目标父目录存在
        dst.parent.mkdir(parents=True, exist_ok=True)

        import shutil
        shutil.move(str(src), str(dst))

        return json.dumps({
            "success": True,
            "source": str(src),
            "destination": str(dst),
            "operation": "move"
        }, ensure_ascii=False)

    except PermissionError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Move failed: {str(e)}"}, ensure_ascii=False)


@mcp.tool()
def copy_file(source: str, destination: str, overwrite: bool = False) -> str:
    """
    复制文件或目录

    Args:
        source: 源路径
        destination: 目标路径
        overwrite: 是否覆盖
    """
    try:
        src = _validate_path(source)
        dst = _validate_path(destination)

        if not src.exists():
            return json.dumps({"error": f"Source not found: {source}"}, ensure_ascii=False)

        if dst.exists() and not overwrite:
            return json.dumps({"error": f"Destination exists (use overwrite=true): {destination}"}, ensure_ascii=False)

        dst.parent.mkdir(parents=True, exist_ok=True)

        if src.is_dir():
            import shutil
            shutil.copytree(src, dst, dirs_exist_ok=overwrite)
            op_type = "directory_copy"
        else:
            import shutil
            shutil.copy2(src, dst)
            op_type = "file_copy"

        return json.dumps({
            "success": True,
            "source": str(src),
            "destination": str(dst),
            "type": op_type
        }, ensure_ascii=False)

    except PermissionError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Copy failed: {str(e)}"}, ensure_ascii=False)


# ==================== Resource 定义 ====================

@mcp.resource("file://{path}")
def get_file_resource(path: str) -> str:
    """
    将文件暴露为 MCP Resource（模型可直接引用）
    访问方式：file:///absolute/path/to/file
    """
    try:
        # 处理 URL 解码
        from urllib.parse import unquote
        decoded_path = unquote(path)

        target = _validate_path(decoded_path)

        if not target.exists():
            return f"Error: File not found: {decoded_path}"

        if target.is_dir():
            # 返回目录列表
            return list_directory(decoded_path)

        # 读取文件内容（限制大小）
        return read_file(decoded_path, limit=50 * 1024)

    except Exception as e:
        return f"Error accessing resource: {str(e)}"


# ==================== Prompt 模板 ====================

@mcp.prompt()
def analyze_code_prompt(file_path: str) -> str:
    """生成代码分析提示模板"""
    return f"""请分析以下代码文件并提供：
1. 代码功能概述
2. 潜在问题或改进建议
3. 安全漏洞检查

文件路径：{file_path}

请先读取文件内容，然后进行详细分析。"""

@mcp.prompt()
def refactor_suggestion_prompt(directory: str, file_pattern: str = "*.py") -> str:
    """生成重构建议提示模板"""
    return f"""请分析目录 {directory} 中符合 {file_pattern} 的代码文件，并提供重构建议：

1. 代码结构优化
2. 设计模式应用
3. 性能改进点
4. 可维护性提升建议

请先搜索相关文件，了解整体架构后再给出建议。"""


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import sys

    # 从命令行参数读取允许的路径（安全沙箱）
    if len(sys.argv) > 1:
        allowed = sys.argv[1:]
        set_allowed_paths(allowed)
        print(f"Security: Restricted to paths: {allowed}", file=sys.stderr)
    else:
        print("Warning: No path restrictions set. All files accessible!", file=sys.stderr)

    # 启动服务器（stdio 模式用于 Claude Desktop，sse 模式用于 Web）
    mcp.run(transport='stdio')