#!/usr/bin/env python3
"""
AI News Daily Page Generator
Accepts news JSON, outputs a mobile-friendly card-based HTML page.

Usage:
  python generate_page.py --data '<json>' --output path/to/output.html --date 2025-06-02
  python generate_page.py --file news.json --output path/to/output.html --date 2025-06-02
"""

import argparse
import json
import sys
import os
from datetime import datetime

TAG_COLORS = {
    "制造业":     "#3b82f6",
    "医疗AI":     "#10b981",
    "金融科技":   "#8b5cf6",
    "物流自动化": "#f59e0b",
    "智能办公":   "#06b6d4",
    "政策监管":   "#ef4444",
    "大模型应用": "#ec4899",
    "机器人":     "#f97316",
    "供应链":     "#84cc16",
    "人力资源":   "#a78bfa",
    "客服AI":     "#22d3ee",
    "代码生成":   "#4ade80",
    "数据分析":   "#fb923c",
    "安全合规":   "#f43f5e",
    "教育培训":   "#34d399",
}

DEFAULT_TAG_COLOR = "#6b7280"

IMPORTANCE_COLORS = {
    "高": "#ef4444",
    "中": "#3b82f6",
}

def tag_color(tag):
    return TAG_COLORS.get(tag, DEFAULT_TAG_COLOR)

def render_tags(tags):
    parts = []
    for t in tags:
        color = tag_color(t)
        parts.append(
            f'<span class="tag" style="background:{color}20;color:{color};border:1px solid {color}40">{t}</span>'
        )
    return "".join(parts)

def render_card(item, index):
    importance = item.get("importance", "中")
    accent = IMPORTANCE_COLORS.get(importance, "#3b82f6")
    tags_html = render_tags(item.get("tags", []))
    source = item.get("source", "")
    pub_time = item.get("pub_time", "")
    meta = " · ".join(filter(None, [source, pub_time]))
    url = item.get("url", "#")
    summary = item.get("summary", "")
    title = item.get("title_zh", item.get("title", ""))

    importance_badge = ""
    if importance == "高":
        importance_badge = f'<span class="importance-badge" style="background:{accent}20;color:{accent}">🔥 重要</span>'

    return f"""
    <article class="card" style="--accent:{accent}" onclick="window.open('{url}','_blank')">
      <div class="card-accent-bar" style="background:{accent}"></div>
      <div class="card-body">
        <div class="card-meta">
          <span class="card-source">{meta}</span>
          {importance_badge}
        </div>
        <h2 class="card-title">{title}</h2>
        <div class="card-tags">{tags_html}</div>
        <p class="card-summary">{summary}</p>
        <div class="card-footer">
          <span class="read-more">阅读原文 →</span>
        </div>
      </div>
    </article>"""

def generate_html(news_items, date_str, generated_at):
    count = len(news_items)
    cards_html = "\n".join(render_card(item, i) for i, item in enumerate(news_items))

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<title>AI 新闻日报 · {date_str}</title>
<meta name="description" content="AI 职场与工业应用每日新闻聚合 {date_str}">
<style>
  :root {{
    --bg: #f8fafc;
    --surface: #ffffff;
    --text: #1e293b;
    --text-secondary: #64748b;
    --border: #e2e8f0;
    --radius: 16px;
    --shadow: 0 2px 12px rgba(0,0,0,0.06);
    --max-width: 480px;
  }}

  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #0f172a;
      --surface: #1e293b;
      --text: #f1f5f9;
      --text-secondary: #94a3b8;
      --border: #334155;
      --shadow: 0 2px 12px rgba(0,0,0,0.3);
    }}
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB",
                 "Microsoft YaHei", sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding-bottom: 40px;
  }}

  .header {{
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 20px 16px 16px;
    position: sticky;
    top: 0;
    z-index: 100;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
  }}

  .header-inner {{
    max-width: var(--max-width);
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}

  .header-logo {{
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.3px;
  }}

  .header-logo span {{
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}

  .header-meta {{
    font-size: 12px;
    color: var(--text-secondary);
    text-align: right;
    line-height: 1.5;
  }}

  .header-date {{
    font-weight: 600;
    font-size: 13px;
    color: var(--text);
  }}

  .update-bar {{
    max-width: var(--max-width);
    margin: 12px auto 0;
    font-size: 11px;
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  .update-dot {{
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #10b981;
    animation: pulse 2s infinite;
  }}

  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.4; }}
  }}

  .news-count {{
    display: inline-block;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    color: white;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 20px;
    margin-left: 6px;
  }}

  main {{
    max-width: var(--max-width);
    margin: 0 auto;
    padding: 16px 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }}

  .card {{
    background: var(--surface);
    border-radius: var(--radius);
    border: 1px solid var(--border);
    box-shadow: var(--shadow);
    overflow: hidden;
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    -webkit-tap-highlight-color: transparent;
    position: relative;
  }}

  .card:active {{ transform: scale(0.98); }}

  @media (hover: hover) {{
    .card:hover {{
      transform: translateY(-2px);
      box-shadow: 0 6px 24px rgba(0,0,0,0.1);
    }}
  }}

  .card-accent-bar {{ height: 3px; width: 100%; }}

  .card-body {{ padding: 14px 16px 16px; }}

  .card-meta {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
    gap: 8px;
  }}

  .card-source {{
    font-size: 11px;
    color: var(--text-secondary);
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}

  .importance-badge {{
    font-size: 10px;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 10px;
    white-space: nowrap;
    flex-shrink: 0;
  }}

  .card-title {{
    font-size: 15px;
    font-weight: 700;
    line-height: 1.45;
    color: var(--text);
    margin-bottom: 10px;
    letter-spacing: -0.2px;
  }}

  .card-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-bottom: 10px;
  }}

  .tag {{
    font-size: 10px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 8px;
    letter-spacing: 0.2px;
  }}

  .card-summary {{
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.65;
    margin-bottom: 12px;
  }}

  .card-footer {{ display: flex; justify-content: flex-end; }}

  .read-more {{
    font-size: 12px;
    font-weight: 600;
    color: #3b82f6;
    letter-spacing: 0.3px;
  }}

  .footer {{
    text-align: center;
    font-size: 11px;
    color: var(--text-secondary);
    padding: 20px 16px 0;
    line-height: 1.8;
  }}

  .footer a {{
    color: var(--text-secondary);
    text-decoration: none;
  }}

  .footer a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>

<header class="header">
  <div class="header-inner">
    <div class="header-logo">⚡ <span>AI 新闻日报</span></div>
    <div class="header-meta">
      <div class="header-date">{date_str}</div>
      <div>今日精选 <span class="news-count">{count} 条</span></div>
    </div>
  </div>
  <div class="update-bar">
    <div class="update-dot"></div>
    <span>AI 职场与工业应用 · 更新于 {generated_at}</span>
  </div>
</header>

<main>
{cards_html}
</main>

<div class="footer">
  <div>来源：TechCrunch · VentureBeat · MIT Technology Review · Reuters · Bloomberg</div>
  <div style="margin-top:8px"><a href="index.html">← 历史归档</a></div>
  <div style="margin-top:8px;opacity:0.5">由 Claude AI 自动生成 · 每天 06:00 更新</div>
</div>

</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="Generate AI News Daily HTML page")
    parser.add_argument("--data", help="News JSON string")
    parser.add_argument("--file", help="Path to news JSON file")
    parser.add_argument("--output", required=True, help="Output HTML file path")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Date string")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8-sig") as f:
            news_items = json.load(f)
    elif args.data:
        news_items = json.loads(args.data)
    else:
        print("Error: provide --data or --file", file=sys.stderr)
        sys.exit(1)

    generated_at = datetime.now().strftime("%H:%M")
    html = generate_html(news_items, args.date, generated_at)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Generated: {args.output} ({len(news_items)} articles)")


if __name__ == "__main__":
    main()
