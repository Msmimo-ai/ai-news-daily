"""
AI News Daily - Fetch & Generate
从权威媒体 RSS 订阅抓取最新AI新闻，调用 Gemini API 处理，生成HTML页面
依赖：google-genai, feedparser, requests
"""

import json
import os
import sys
import subprocess
import time
from datetime import datetime, timezone, timedelta
from groq import Groq
import feedparser
import requests

TODAY = datetime.now().strftime("%Y-%m-%d")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")
OUTPUT_HTML = os.path.join(OUTPUT_DIR, f"ai-news-{TODAY}.html")
GENERATE_SCRIPT = os.path.join(os.path.dirname(__file__), "generate_page.py")

# 权威 AI 媒体 RSS 源
RSS_FEEDS = [
    ("TechCrunch",          "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat",         "https://venturebeat.com/category/ai/feed/"),
    ("MIT Technology Review","https://www.technologyreview.com/feed/"),
    ("The Verge",           "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("Wired",               "https://www.wired.com/feed/tag/artificial-intelligence/latest/rss"),
    ("Reuters Technology",  "https://feeds.reuters.com/reuters/technologyNews"),
    ("Ars Technica AI",     "https://feeds.arstechnica.com/arstechnica/technology-lab"),
]

FILTER_PROMPT = """你是一名专为工业流程工程师（Process Engineer）服务的AI新闻编辑。

读者画像：制造业/化工/能源等行业的流程工程师，已在用或想用AI工具提升工作效率，目标是成为团队里最懂AI、最会用AI的人。阅读目的是：了解行业AI应用趋势、发现可以直接上手的AI工具。

下面是从权威媒体RSS收集的最新AI新闻候选列表。

**任务一：筛选9条新闻**

筛选标准：
- AI在制造、化工、能源、物流、质量管理、工程设计等工业场景的实际落地
- 对工程师日常工作有直接帮助的AI工具或功能发布
- 有具体公司名、数据、结果的案例，而非泛泛而谈

**去重规则（重要）**：若多条新闻报道的是同一件事（即使来源不同、角度略有差异），只保留信息最完整的那一条，其余全部丢弃。判断是否重复的标准是：核心事件相同（同一家公司、同一个产品、同一次发布）。

过滤掉：纯学术论文、炒作标题、娱乐/游戏/艺术AI、消费者产品（与工业无关）。

**任务二：生成1篇 Copilot 实操课题**

设计一个本周的 Copilot 实操小课题，让流程工程师能在工作中立刻动手实践。要求：
- 使用 Microsoft Copilot（可以是 Copilot in Excel、Word、Teams、Outlook 或 Copilot Studio）
- 与流程工程师的真实工作场景高度相关（如：SOP撰写、数据分析、设备异常报告、工艺参数优化建议、培训材料制作等）
- 有完整的分步操作说明（6-10步），每步说清楚：打开什么、输入什么、得到什么
- 读者按步骤操作完后能得到一个可以直接使用的成品工具或文档
- 难度适中，30分钟内可以完成

**输出格式**：直接输出一个JSON数组（不要加```标记），共10条，前9条是新闻，最后1条是实操课题。

新闻条目字段：
- type: "news"
- title_zh: 中文标题（不超过30字）
- summary: 中文摘要（150-200字，说清楚：发生了什么、关键数据、对工业/工程师的实际意义）
- tags: 3-5个标签，从以下选：制造业/医疗AI/金融科技/物流自动化/智能办公/政策监管/大模型应用/机器人/供应链/人力资源/代码生成/数据分析/安全合规/质量管理/工程设计
- importance: "高"或"中"
- source: 来源媒体名称
- pub_time: 发布日期 YYYY-MM-DD
- url: 原文链接

实操课题条目字段：
- type: "tutorial"
- title_zh: 课题标题（吸引人，20字以内，如"用 Copilot 10分钟生成设备异常分析报告"）
- summary: 课题背景介绍（100字，说明这个工具解决什么痛点、做完能得到什么）
- steps: 操作步骤数组，每步是一个字符串，格式"第N步：[动作]——[具体输入或操作内容]——[预期结果]"
- tags: ["Copilot实操", "工程师必学"]
- importance: "高"
- source: "本期实操课题"
- pub_time: 今天日期
- url: "https://copilot.microsoft.com"

候选新闻列表：
{candidates}

只输出JSON数组，不要任何解释文字。"""


def fetch_rss_news():
    """从多个 RSS 源抓取最近 48 小时的新闻"""
    results = []
    seen_urls = set()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    headers = {"User-Agent": "Mozilla/5.0 (compatible; AI-News-Bot/1.0)"}

    for source_name, feed_url in RSS_FEEDS:
        try:
            resp = requests.get(feed_url, headers=headers, timeout=15)
            feed = feedparser.parse(resp.content)
            count = 0
            for entry in feed.entries:
                url = entry.get("link", "")
                if not url or url in seen_urls:
                    continue

                # 解析发布时间
                pub_date = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

                if pub_date and pub_date < cutoff:
                    continue  # 跳过 48 小时前的旧闻

                title = entry.get("title", "")
                summary = entry.get("summary", "") or entry.get("description", "")
                # 去除 HTML 标签
                import re
                summary = re.sub(r"<[^>]+>", " ", summary).strip()[:300]

                seen_urls.add(url)
                results.append({
                    "title": title,
                    "body": summary,
                    "source": source_name,
                    "date": pub_date.strftime("%Y-%m-%d") if pub_date else TODAY,
                    "url": url,
                })
                count += 1
                if count >= 10:  # 每个源最多取 10 条
                    break

            print(f"  {source_name}: {count} 条")
        except Exception as e:
            print(f"  {source_name} 抓取失败: {e}", file=sys.stderr)

        time.sleep(0.5)  # 礼貌性延迟

    print(f"共抓取 {len(results)} 条候选新闻")
    return results


def format_candidates(raw_news):
    lines = []
    for i, n in enumerate(raw_news, 1):
        lines.append(
            f"{i}. [{n['source']}] {n['date']}\n"
            f"   标题: {n['title']}\n"
            f"   摘要: {n['body'][:250]}\n"
            f"   链接: {n['url']}"
        )
    return "\n\n".join(lines)


def process_with_groq(raw_news):
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    candidates_text = format_candidates(raw_news)
    prompt = FILTER_PROMPT.format(candidates=candidates_text)

    print("调用 Groq API 处理新闻...")
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    raw_output = response.choices[0].message.content.strip()

    # 去除可能的 markdown 代码块标记
    if raw_output.startswith("```"):
        raw_output = "\n".join(raw_output.split("\n")[1:])
    if raw_output.endswith("```"):
        raw_output = "\n".join(raw_output.split("\n")[:-1])

    news_items = json.loads(raw_output)
    print(f"筛选保留 {len(news_items)} 条新闻")
    return news_items


def generate_html(news_items):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tmp_json = os.path.join(OUTPUT_DIR, f"_tmp_{TODAY}.json")
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(news_items, f, ensure_ascii=False, indent=2)

    result = subprocess.run(
        [sys.executable, GENERATE_SCRIPT,
         "--file", tmp_json, "--output", OUTPUT_HTML, "--date", TODAY],
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
    pages = sorted(glob.glob(os.path.join(OUTPUT_DIR, "ai-news-????-??-??.html")), reverse=True)
    archive_items = ""
    for p in pages[:30]:
        d = os.path.basename(p).replace("ai-news-", "").replace(".html", "")
        mark = "✦ " if d == TODAY else ""
        archive_items += f'<li><a href="ai-news-{d}.html">{mark}{d}</a></li>\n'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 新闻日报</title>
<meta http-equiv="refresh" content="0;url=ai-news-{TODAY}.html">
<style>
  body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;max-width:480px;margin:60px auto;padding:0 20px;color:#1e293b}}
  h1{{font-size:24px;margin-bottom:8px}}p{{color:#64748b;margin-bottom:24px}}
  ul{{list-style:none;padding:0}}li{{margin:8px 0}}
  a{{color:#3b82f6;text-decoration:none}}a:hover{{text-decoration:underline}}
</style>
</head>
<body>
<h1>⚡ AI 新闻日报</h1>
<p>AI 职场与工业应用每日精选，正在跳转今日页面…</p>
<p style="font-size:13px;color:#94a3b8">如未自动跳转，<a href="ai-news-{TODAY}.html">点击这里</a></p>
<h2 style="font-size:16px;margin-top:32px">历史归档</h2>
<ul>{archive_items}</ul>
</body></html>"""

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html 已更新")


def main():
    print(f"=== AI News Daily {TODAY} ===")
    if not os.environ.get("GROQ_API_KEY"):
        print("ERROR: 未设置 GROQ_API_KEY", file=sys.stderr)
        sys.exit(1)

    print("抓取 RSS 新闻源...")
    raw_news = fetch_rss_news()
    if not raw_news:
        print("ERROR: 未抓取到任何新闻", file=sys.stderr)
        sys.exit(1)

    news_items = process_with_groq(raw_news)
    generate_html(news_items)
    update_index()
    print(f"完成！{OUTPUT_HTML}")


if __name__ == "__main__":
    main()
