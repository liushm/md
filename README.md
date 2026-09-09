# md-webdav

一个极简的 WebDAV 文件备份命令。

## 安装依赖

```powershell
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv sync
```

## 配置

复制示例配置：

```powershell
Copy-Item md.example.toml md.toml
```

编辑 `md.toml`：

```toml
[webdav]
base_url = "https://dav.example.com"
remote_dir = "/backup"
username = "username"
password = "password"
proxy = "socks5h://127.0.0.1:7890"
timeout_seconds = 120.0
max_size_mib = 5
```

本地 `md.toml` 已加入 `.gitignore`，不会进入 Git 提交或 Python 安装包。

程序按以下顺序查找配置：

1. `MD_CONFIG` 环境变量指定的文件
2. 当前目录的 `md.toml`
3. 项目根目录的 `md.toml`
4. Windows `%APPDATA%\md\config.toml`
5. `~/.config/md/config.toml`

## 使用

上传文件或文件夹：

```powershell
uv run md push C:\path\to\.vimrc
uv run md push C:\path\to\config-folder
```

如果远程目录已经存在同名内容，命令会报错，不会覆盖。上传内容超过 5 MiB 时会询问是否继续。

列出远程内容：

```powershell
uv run md ls
```

下载远程文件或文件夹到当前目录：

```powershell
uv run md get .vimrc
uv run md get config-folder
```

删除远程文件或文件夹：

```powershell
uv run md rm .vimrc
uv run md rm config-folder
```

删除前会要求确认。

## 安装命令

```powershell
uv tool install --editable .
```

Windows PowerShell 和 CMD 已经将 `md` 用作创建目录命令，所以安装后建议显式执行：

```powershell
md.exe ls
```

PowerShell 当前会话如果希望直接使用 `md`，可以先删除内置别名：

```powershell
Remove-Item Alias:md
md ls
```

`md.exe` 只是 Python 命令入口，不包含账号密码。账号密码保存在外部 `md.toml` 中。

## 测试

```powershell
uv run python -m unittest discover -s tests -v
```

## 打包 Windows EXE

项目使用 PyInstaller 生成单文件命令行程序：

```powershell
.\scripts\build.ps1
```

生成结果：

```text
dist\md.exe
```

运行：

```powershell
.\dist\md.exe ls
.\dist\md.exe push C:\path\to\.vimrc
.\dist\md.exe get .vimrc
.\dist\md.exe rm .vimrc
```

`md.exe` 不包含账号密码。将 `md.toml` 放在运行命令时的当前目录，或者放到：

```text
%APPDATA%\md\config.toml
```

也可以用环境变量指定：

```powershell
$env:MD_CONFIG = "D:\private\md.toml"
.\dist\md.exe ls
```

PyInstaller 只能为当前操作系统生成程序；Windows 版需要在 Windows 上构建。
