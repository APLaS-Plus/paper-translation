"""Paper Translation MCP Server — 参考文献查找 & arXiv 查询工具.

通过 stdio JSON-RPC 与 Claude Code 通信。
翻译 agent 可调用这些工具来解析参考文献链接，弥补 MinerU 不输出 URL 的缺陷。
"""

import json
import sys
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from typing import Any


# ── CrossRef API ────────────────────────────────────────────

def _crossref_search(title: str, author: str = "", rows: int = 3) -> list[dict]:
    """Search CrossRef for papers matching title (+ optional author)."""
    query = title
    if author:
        query = f"{title} {author}"
    url = (
        "https://api.crossref.org/works?"
        + urllib.parse.urlencode({
            "query": query,
            "rows": rows,
            "select": "DOI,title,author,URL,container-title,issued",
        })
    )
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "PaperTranslationSkill/1.0 (mailto:202300204004@stumail.sztu.edu.cn)")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        items = data.get("message", {}).get("items", [])
    except Exception as e:
        return [{"error": str(e)}]

    results = []
    for item in items:
        authors = item.get("author", [])
        author_names = ", ".join(
            f"{a.get('given', '')} {a.get('family', '')}".strip()
            for a in (authors or [])[:3]
        )
        date_parts = item.get("issued", {}).get("date-parts", [[None]])[0]
        year = date_parts[0] if date_parts else None
        results.append({
            "title": item.get("title", [""])[0],
            "doi": item.get("DOI", ""),
            "url": item.get("URL", f"https://doi.org/{item['DOI']}" if item.get("DOI") else ""),
            "authors": author_names,
            "year": year,
            "container": item.get("container-title", [""])[0] if item.get("container-title") else "",
        })
    return results


# ── arXiv API ────────────────────────────────────────────────

def _arxiv_lookup(arxiv_id: str) -> dict | None:
    """Look up arXiv paper metadata by ID."""
    url = f"http://export.arxiv.org/api/query?search_query=id:{arxiv_id}&max_results=1"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            xml_data = resp.read().decode("utf-8")
    except Exception as e:
        return {"error": str(e)}

    root = ET.fromstring(xml_data)
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    entry = root.find("atom:entry", ns)
    if entry is None:
        return None

    title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
    summary = entry.findtext("atom:summary", "", ns).strip().replace("\n", " ")
    published = entry.findtext("atom:published", "", ns)
    pdf_link = ""
    for link in entry.findall("atom:link", ns):
        if link.get("title") == "pdf":
            pdf_link = link.get("href", "")
    authors = [
        a.findtext("atom:name", "", ns).strip()
        for a in entry.findall("atom:author", ns)
    ]
    # Extract DOI from entry
    doi = ""
    for link in entry.findall("atom:link", ns):
        href = link.get("href", "")
        if "doi.org" in href:
            doi = href.replace("http://dx.doi.org/", "").replace("https://doi.org/", "")
    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": ", ".join(authors[:5]),
        "published": published,
        "summary": summary[:500],
        "pdf_url": pdf_link,
        "doi": doi,
        "abstract_url": f"https://arxiv.org/abs/{arxiv_id}",
    }


def _arxiv_search(query: str, max_results: int = 5) -> list[dict]:
    """Search arXiv for papers."""
    url = (
        "http://export.arxiv.org/api/query?"
        + urllib.parse.urlencode({
            "search_query": f"all:{query}",
            "max_results": max_results,
            "sortBy": "relevance",
        })
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            xml_data = resp.read().decode("utf-8")
    except Exception as e:
        return [{"error": str(e)}]

    root = ET.fromstring(xml_data)
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    results = []
    for entry in root.findall("atom:entry", ns):
        title = entry.findtext("atom:title", "", ns).strip().replace("\n", " ")
        arxiv_id = entry.findtext("atom:id", "", ns).strip()
        # Extract just the ID part from the full URL
        if "/abs/" in arxiv_id:
            arxiv_id = arxiv_id.split("/abs/")[-1]
        authors = [
            a.findtext("atom:name", "", ns).strip()
            for a in entry.findall("atom:author", ns)
        ]
        results.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": ", ".join(authors[:3]),
            "published": entry.findtext("atom:published", "", ns),
        })
    return results


# ── MCP Server ───────────────────────────────────────────────

def handle_request(request: dict) -> dict | None:
    """Handle a single JSON-RPC request; returns response or None for notifications."""
    method = request.get("method", "")
    req_id = request.get("id")

    # initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": "paper-translation-mcp",
                    "version": "1.0.0",
                },
            },
        }

    # tools/list
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "resolve_reference",
                        "description": (
                            "通过 CrossRef API 查找学术论文的 DOI 和 URL。"
                            "输入论文标题（必填）和可选作者名，返回匹配的文献信息（DOI、URL、作者、年份、期刊）。"
                            "用于翻译流程的 Fix 阶段——MinerU 不提供参考文献链接，可用此工具批量补全。"
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "论文标题（必填），支持部分匹配",
                                },
                                "author": {
                                    "type": "string",
                                    "description": "可选：作者名，用于缩小搜索范围",
                                },
                            },
                            "required": ["title"],
                        },
                    },
                    {
                        "name": "lookup_arxiv",
                        "description": (
                            "查询 arXiv 论文的元数据（标题、作者、摘要、DOI、PDF 链接）。"
                            "输入 arXiv ID（如 1910.09615 或 1910.09615v1），返回完整元数据。"
                            "用于验证翻译中引用的 arXiv 论文信息。"
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "arxiv_id": {
                                    "type": "string",
                                    "description": "arXiv ID，如 2502.12391 或 2502.12391v2",
                                },
                            },
                            "required": ["arxiv_id"],
                        },
                    },
                    {
                        "name": "search_arxiv",
                        "description": (
                            "在 arXiv 上搜索论文。输入关键词，返回匹配论文列表。"
                            "用于发现相关论文或验证论文引用。"
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "搜索关键词",
                                },
                                "max_results": {
                                    "type": "integer",
                                    "description": "最大返回数量（默认 5，最多 10）",
                                    "default": 5,
                                },
                            },
                            "required": ["query"],
                        },
                    },
                    {
                        "name": "batch_resolve_references",
                        "description": (
                            "批量解析参考文献列表。输入多行参考文献文本（每条一行或一段），"
                            "提取标题关键词并发查询 CrossRef，返回每个文献的 DOI 和 URL。"
                            "这是 Fix 阶段的核心工具——一次性补全整篇论文的参考文献链接。"
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "references": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "参考文献文本列表，每条一个元素",
                                },
                            },
                            "required": ["references"],
                        },
                    },
                ],
            },
        }

    # tools/call
    if method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        result_text = ""
        try:
            if tool_name == "resolve_reference":
                title = arguments.get("title", "")
                author = arguments.get("author", "")
                results = _crossref_search(title, author)
                if not results:
                    result_text = f"未找到匹配文献: {title}"
                elif "error" in results[0]:
                    result_text = f"CrossRef API 错误: {results[0]['error']}"
                else:
                    lines = []
                    for i, r in enumerate(results):
                        lines.append(
                            f"[{i+1}] {r['title']}\n"
                            f"    DOI: {r['doi']}\n"
                            f"    URL: {r['url']}\n"
                            f"    Authors: {r['authors']}\n"
                            f"    Year: {r['year']}  Journal: {r['container']}"
                        )
                    result_text = "\n\n".join(lines)

            elif tool_name == "lookup_arxiv":
                arxiv_id = arguments.get("arxiv_id", "")
                result = _arxiv_lookup(arxiv_id)
                if result is None:
                    result_text = f"未找到 arXiv 论文: {arxiv_id}"
                elif "error" in result:
                    result_text = f"arXiv API 错误: {result['error']}"
                else:
                    result_text = (
                        f"Title: {result['title']}\n"
                        f"Authors: {result['authors']}\n"
                        f"Published: {result['published']}\n"
                        f"DOI: {result['doi']}\n"
                        f"arXiv: https://arxiv.org/abs/{result['arxiv_id']}\n"
                        f"PDF: {result['pdf_url']}\n"
                        f"Abstract: {result['summary']}..."
                    )

            elif tool_name == "search_arxiv":
                query = arguments.get("query", "")
                max_results = min(int(arguments.get("max_results", 5)), 10)
                results = _arxiv_search(query, max_results)
                if not results:
                    result_text = f"未找到 arXiv 论文: {query}"
                elif "error" in results and "error" in results[0]:
                    result_text = f"arXiv API 错误: {results[0]['error']}"
                else:
                    lines = []
                    for r in results:
                        lines.append(
                            f"arXiv: {r['arxiv_id']}  {r['title']}\n"
                            f"  Authors: {r['authors']}  Published: {r['published']}"
                        )
                    result_text = "\n\n".join(lines)

            elif tool_name == "batch_resolve_references":
                refs = arguments.get("references", [])
                if not refs:
                    result_text = "参考文献列表为空"
                else:
                    lines = []
                    found = 0
                    for i, ref_text in enumerate(refs):
                        # Extract first 6 words as a rough title query
                        words = ref_text.strip().split()
                        title_query = " ".join(words[:8]) if len(words) >= 3 else ref_text.strip()
                        results = _crossref_search(title_query, rows=1)
                        if results and "error" not in results[0] and results[0].get("doi"):
                            r = results[0]
                            lines.append(
                                f"[{i+1}] {r['doi']} → {r['url']}"
                            )
                            found += 1
                        else:
                            lines.append(f"[{i+1}] ❌ 未找到: {ref_text[:80]}...")
                    lines.insert(0, f"共 {len(refs)} 条，找到 {found} 条 DOI ({found*100//len(refs)}%)")
                    result_text = "\n".join(lines)

            else:
                result_text = f"未知工具: {tool_name}"

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"工具执行错误: {e}"}],
                    "isError": True,
                },
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": result_text}],
            },
        }

    # notifications/no-id requests — silently skip
    if req_id is None:
        return None

    # Unknown method
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main():
    """Run the MCP server on stdio."""
    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
        except json.JSONDecodeError:
            continue
        response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
