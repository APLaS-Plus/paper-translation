"""使用 MinerU Precision API 批量解析 PDF，输出含图片的完整文档

环境变量:
  MINERU_TOKEN: JWT token (在 https://mineru.net 控制台获取)
  MINERU_BASE_URL: API 地址 (默认 https://mineru.net/api/v4)
"""

import time, os, subprocess, zipfile, io
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent
API_BASE = os.environ.get("MINERU_BASE_URL", "https://mineru.net/api/v4")
# 优先从环境变量读取，其次从 skill 配置文件
TOKEN = os.environ.get("MINERU_TOKEN", "")
if not TOKEN:
    config_path = Path.home() / ".claude" / "skills" / "paper-translation" / "config"
    if config_path.exists():
        for line in config_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("MINERU_TOKEN="):
                TOKEN = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

if not TOKEN:
    raise RuntimeError(
        "请先配置 MinerU API Token:\n"
        "  1. 访问 https://mineru.net/apiManage/token 获取 JWT Token\n"
        "  2. 填入 ~/.claude/skills/paper-translation/config 文件中\n"
        "  3. 或设置环境变量 MINERU_TOKEN"
    )

# 要解析的 PDF 列表: {"path": "相对路径", "data_id": "唯一标识"}
PDFS = [
    {"path": "2605.13058v1.pdf", "data_id": "2605.13058v1"},
]

os.environ["no_proxy"] = "mineru.net,openxlab.org.cn"


def make_session() -> requests.Session:
    s = requests.Session()
    s.trust_env = False
    s.headers.update({
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    })
    return s


def batch_upload(session: requests.Session):
    """批量上传 PDF，返回 (batch_id, [upload_url, ...])"""
    print("\n[1/4] 申请上传链接...")
    resp = session.post(f"{API_BASE}/file-urls/batch", json={
        "files": [{"name": p["path"], "data_id": p["data_id"]} for p in PDFS],
        "model_version": "vlm",
        "language": "en",
        "extra_formats": ["docx"],
    })
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"申请上传链接失败: {data}")
    batch_id = data["data"]["batch_id"]
    file_urls = data["data"]["file_urls"]
    print(f"  batch_id: {batch_id}")
    return batch_id, file_urls


def upload_files(file_urls: list[str]):
    """PUT 上传文件到 OSS"""
    print("[2/4] 上传文件...")
    for i, upload_url in enumerate(file_urls):
        filepath = BASE_DIR / PDFS[i]["path"]
        size_kb = filepath.stat().st_size / 1024
        print(f"  -> {PDFS[i]['path']} ({size_kb:.0f} KB)", end="", flush=True)
        put = requests.put(upload_url, data=open(filepath, "rb"), headers={"Content-Type": ""})
        if put.status_code not in (200, 204):
            raise RuntimeError(f"上传失败 HTTP {put.status_code}: {put.text[:200]}")
        print("  OK")


def poll_batch(session: requests.Session, batch_id: str, timeout: int = 600) -> list[dict]:
    """轮询批量解析结果"""
    print("[3/4] 等待解析...", end="", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        resp = session.get(f"{API_BASE}/extract-results/batch/{batch_id}")
        data = resp.json()
        if data.get("code") != 0:
            print(f"\n  查询失败: {data}")
            time.sleep(3)
            continue
        results = data["data"]["extract_result"]
        states = [r["state"] for r in results]
        if all(s == "done" for s in states):
            print(" 完成!")
            return results
        if any(s == "failed" for s in states):
            for r in results:
                if r["state"] == "failed":
                    print(f"\n  [失败] {r['file_name']}: {r.get('err_msg', '')}")
            raise RuntimeError("有任务失败")
        print(".", end="", flush=True)
        time.sleep(3)
    raise TimeoutError(f"超时 ({timeout}s)")


def download_results(results: list[dict]):
    """下载并解压解析结果"""
    print("[4/4] 下载结果...")
    for r in results:
        fname = r["file_name"]
        zip_url = r["full_zip_url"]
        out_dir = BASE_DIR / f"output_{Path(fname).stem}"

        if out_dir.exists() and any(out_dir.iterdir()):
            n_files = len(list(out_dir.rglob("*")))
            print(f"  [跳过] {fname} (已有 {n_files} 文件)")
            continue

        out_dir.mkdir(exist_ok=True)
        print(f"  -> {fname}", end="", flush=True)
        try:
            resp = requests.get(zip_url, verify=False, timeout=120)
        except requests.exceptions.SSLError:
            zip_path = out_dir / "result.zip"
            subprocess.run(
                ["curl", "-k", "-L", "-s", "-o", str(zip_path), zip_url],
                timeout=120, check=True,
            )
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(out_dir)
            zip_path.unlink()
        else:
            resp.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                zf.extractall(out_dir)

        files = list(out_dir.rglob("*"))
        print(f" OK ({len(files)} files)")
        for f in sorted(out_dir.iterdir()):
            prefix = "[DIR]" if f.is_dir() else "     "
            print(f"    {prefix} {f.name}")


def main():
    if not PDFS:
        print("请先在 PDFS 列表中添加要解析的 PDF 文件路径")
        return
    session = make_session()
    try:
        batch_id, file_urls = batch_upload(session)
        upload_files(file_urls)
        results = poll_batch(session, batch_id)
        download_results(results)
        print("\n[DONE] All completed!")
    except Exception as e:
        print(f"\n[ERROR] {e}")


if __name__ == "__main__":
    main()
