#!/usr/bin/env python3
"""
一键推送 ScienceCopilot 到 GitHub（含子目录）。
运行后输入 GitHub Personal Access Token 即可。
"""
import getpass
import os
import subprocess
import sys

REPO_DIR = r"D:\学习\AI项目\ScienceCopilot"
REMOTE_URL_TEMPLATE = "https://{token}@github.com/Zhf0826/ScienceCopilot.git"

# WorkBuddy 自带的 PortableGit 路径
GIT_CANDIDATES = [
    r"C:\Users\zhf\.workbuddy\binaries\PortableGit\versions\1.2.0\mingw64\bin\git.exe",
    r"C:\Program Files\Git\mingw64\bin\git.exe",
    r"C:\Program Files\Git\bin\git.exe",
    r"C:\Program Files\Git\cmd\git.exe",
    r"C:\Program Files (x86)\Git\bin\git.exe",
]


def find_git() -> str:
    for path in GIT_CANDIDATES:
        if os.path.isfile(path):
            return path
    sys.exit("错误：找不到 git.exe，请确认已安装 Git for Windows。")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print("$ " + " ".join(cmd))
    return subprocess.run(cmd, cwd=REPO_DIR, check=True, **kwargs)


def main() -> None:
    git = find_git()
    print(f"使用 git: {git}")
    print()

    token = getpass.getpass("请输入 GitHub Personal Access Token（输入时不显示）: ").strip()
    if not token:
        sys.exit("Token 不能为空。")

    os.chdir(REPO_DIR)

    # 移除旧的 origin（如果存在）
    subprocess.run([git, "remote", "remove", "origin"], cwd=REPO_DIR, capture_output=True)

    # 添加带 token 的 origin
    remote_url = REMOTE_URL_TEMPLATE.format(token=token)
    run([git, "remote", "add", "origin", remote_url])

    # 确保分支名为 main
    run([git, "branch", "-M", "main"])

    # 强制推送完整仓库（会覆盖 GitHub 上现有内容）
    print()
    print("正在推送到 GitHub...")
    run([git, "push", "-u", "origin", "main", "--force"])

    print()
    print("✅ 推送成功！请访问 https://github.com/Zhf0826/ScienceCopilot 确认文件完整。")


if __name__ == "__main__":
    main()
