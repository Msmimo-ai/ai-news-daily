"""
AI News Daily - Fetch & Generate
搜索最近24小时AI职场与工业应用新闻，调用 Gemini API 处理，生成HTML页面
依赖：google-generativeai, duckduckgo-search, requests, beautifulsoup4
"""

import google.generativeai as genai
import json
import os
import sys
import subprocess
from datetime import datetime
from duckduckgo_search import DDGS

TODAY = datetime.now().strftime("%Y-%m-%d")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")
OUTPUT_HTML = os.path.join(OUTPUT_DIR, f"ai-news-{TODAY}.html")
GENERATE_SCRIPT = os.path.join(os.path.dirname(__file__), "generate_page.py")

SEARCH_QUERIES = [
    "AI enterprise deployment workplace automation 2026",
    "artificial intelligence manufacturing industrial application 2026",
    "AI healthcare logistics supply chain 2026",
    "enterprise AI agent launch product 2026",
    "AI workplace productivity tool enterprise 2026",
]

FILTER_PROMPT = """你是一名专业的AI行业新闻编辑。下面是一批从搜索引擎收集的候选新闻摘要。

请从中筛选出8-12条**最有价值**的新闻，标准：
- AI在具体行业的落地案例（有公司名、数据、结果）
- 大型企业AI产品发布且直接影响职场/生产流程
- 政策/报告有明确工业应用导向

过滤掉：纯学术论文、炒作标题、超过48小时旧闻、娱乐/游戏/艺术AI、重复新闻只保留最权威来源。

对每条保留的新闻输出严格的JSON数组（不要加```json标记），字段：
- title_zh: 中文标题（不超过30字）
- summary: 中文摘要（50-100字，包含公司名/数字/影响）
- tags: 3-5个标签数组，从以下选：制造业/医疗AI/金融科技/物流自动化/智能办公/政策监管/大模型应用/机器人/供应链/人力资源/客服AI/代码生成/数据分析/安全合规/教育培训
- importance: "高"或"中"（高=有具体数据+重大影响，每批最多4条）
- source: 来源媒体英文名
- pub_time: 发布日期（YYYY-MM-DD或YYYY-MM）
- url: 原文链接

候选新闻：
{candidates}

直接输出JSON数组，不要任何解释文字。"""


def search_news():
    results = []
    seen_urls = set()
    with DDGS() as ddgs:
        for query in SEARCH_QUERIES:
            try:
                hits = list(ddgs.news(query, max_results=8, timelimit="d"))
                for h in hits:
                    url = h.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        results.append({
                            "title": h.get("title", ""),
                            "body": h.get("body", ""),
                            "source": h.get("source", ""),
                            "date": h.get("date", ""),
                            "url": url,
                        })
            except Exception as e:
                print(f"搜索失败 [{query[:30]}]: {e}", file=sys.stderr)
    print(f"搜索到 {len(results)} 条候选新闻")
    return results


def format_candidates(raw_news):
    lines = []
    for i, n in enumerate(raw_news, 1):
        lines.append(
            f"{i}. [{n['source']}] {n['date']}\n"
            f"   标题: {n['title']}\n"
            f"   摘要: {n['body'][:200]}\n"
            f"   链接: {n['url']}"
        )
    return "\n\n".join(lines)


def process_with_gemini(raw_news):
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")

    candidates_text = format_candidates(raw_news)
    prompt = FILTER_PROMPT.format(candidates=candidates_text)

    print("调用 Gemini API 处理新闻...")
    response = model.generate_content(prompt)
    raw_output = response.text.strip()

    # 容错：去除可能的 markdown 代码块
    if raw_output.startswith("```"):
        raw_output = "\n".join(raw_output.split("\n")[1:])
    if raw_output.endswith("```"):
        raw_output = "\n".join(raw_output.split("\n")[:-1])

    news_items = json.loads(raw_output)
    print(f"Gemini 筛选保留 {len(news_items)} 条新闻")
    return news_items


def generate_html(news_items):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tmp_json = os.path.join(OUTPUT_DIR, f"_tmp_{TODAY}.json")
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(news_items, f, ensure_ascii=False, indent=2)

    result = subprocess.run(
        [sys.executable, GENERATE_SCRIPT,
         "--file", tmp_json,
         "--output", OUTPUT_HTML,
         "--date", TODAY],
        capture_output=True, text=True,
        env={**os.environ, "PYTHONUTF8": "1"}
    )
    os.remove(tmp_json)

    if result.returncode != 0:
        print(f"generate_page.py 错误: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout.strip())


def update_index():
    import glob
    index_path = os.path.join(OUTPUT_DIR, "index.html")
    pages = sorted(
        glob.glob(os.path.join(OUTPUT_DIR, "ai-news-????-??-??.html")),
        reverse=True
    )

    archive_items = ""
    for p in pages[:30]:
        date_str = os.path.basename(p).replace("ai-news-", "").replace(".html", "")
        is_today = "✦ " if date_str == TODAY else ""
        archive_items += f'<li><a href="ai-news-{date_str}.html">{is_today}{date_str}</a></li>\n'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 新闻日报</title>
<meta http-equiv="refresh" content="0;url=ai-news-{TODAY}.html">
<style>
  body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;max-width:480px;margin:60px auto;padding:0 20px;color:#1e293b}}
  h1{{font-size:24px;margin-bottom:8px}}p{{color:#64748b;margin-bottom:24px}}
  ul{{list-style:none;padding:0}}li{{margin:8px 0}}
  a{{color:#3b82f6;text-decoration:none;font-size:15px}}a:hover{{text-decoration:underline}}
</style>
</head>
<body>
<h1>⚡ AI 新闻日报</h1>
<p>AI 职场与工业应用每日精选，正在跳转今日页面…</p>
<p style="font-size:13px;color:#94a3b8">如未自动跳转，<a href="ai-news-{TODAY}.html">点击这里</a></p>
<h2 style="font-size:16px;margin-top:32px">历史归档</h2>
<ul>{archive_items}</ul>
</body>
</html>"""

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"index.html 已更新")


def main():
    print(f"=== AI News Daily {TODAY} ===")

    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: 未设置 GEMINI_API_KEY 环境变量", file=sys.stderr)
        sys.exit(1)

    raw_news = search_news()
    if not raw_news:
        print("ERROR: 未搜索到任何新闻", file=sys.stderr)
        sys.exit(1)

    news_items = process_with_gemini(raw_news)
    generate_html(news_items)
    update_index()
    print(f"完成！输出文件：{OUTPUT_HTML}")


if __name__ == "__main__":
    main()
