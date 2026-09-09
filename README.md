# md-webdav

一个极简的 WebDAV 文件备份命令。

## 配置

连接配置位于：

```text
src/md_webdav/config.py
```

项目已经根据当前测试脚本生成配置。示例配置见 `config.example.py`。

## 安装依赖

```powershell
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv sync
```

## 使用

上传文件或文件夹：

```powershell
uv run md push C:\path\to\.vimrc
uv run md push C:\path\to\config-folder
```

如果远程目录已经存在同名文件或文件夹，命令会报错，不会覆盖。上传内容超过 5 MiB 时会询问是否继续。

列出远程内容：

```powershell
uv run md ls
```

下载远程文件或文件夹到当前目录：

```powershell
uv run md get .vimrc
uv run md get config-folder
```

如果当前目录已经存在同名内容，命令会报错，不会覆盖。

## Windows 的 `md` 命令冲突

PowerShell 和 CMD 已经将 `md` 用作创建目录命令，因此推荐通过 uv 执行：

```powershell
uv run md ls
```

安装后也可以显式执行：

```powershell
md.exe ls
```

PowerShell 当前会话如果希望直接使用 `md`，可以先删除内置别名：

```powershell
Remove-Item Alias:md
md ls
```

## 测试

```powershell
uv run python -m unittest discover -s tests -v
```
