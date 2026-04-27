import os
import subprocess


def 发布到草稿箱(
    md2wechat_script: str,
    markdown_path: str,
    mode: str = "api",
    theme: str = "default",
    cover: str = ""
) -> dict:
    cmd = ["bash", md2wechat_script, "convert", markdown_path, "--mode", mode, "--draft"]

    if mode == "ai" and theme:
        cmd.extend(["--theme", theme])

    if cover:
        cmd.extend(["--cover", cover])

    env = os.environ.copy()
    md2wechat_api_key = env.get("MD2WECHAT_API_KEY", "").strip()
    if not md2wechat_api_key:
        try:
            from 中台工具 import 读取_yaml
            config = 读取_yaml(os.path.expanduser("~/.config/md2wechat/config.yaml"))
            md2wechat_api_key = str(config.get("md2wechat", {}).get("api_key", "")).strip()
        except Exception:
            md2wechat_api_key = ""
    if mode == "api" and md2wechat_api_key:
        cmd.extend(["--api-key", md2wechat_api_key])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
    )

    combined_output = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
    if result.returncode != 0:
        raise RuntimeError(combined_output or "md2wechat 执行失败")

    return {
        "success": True,
        "command": cmd,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "raw_output": combined_output,
    }
