"""
意思決定株式会社 GA4アナリティクス → Ontology Markdown出力スクリプト
実行: python fetch_analytics.py
出力: C:/Users/yukic/マイドライブ/アクションログ/web_analytics/ に月次レポートを保存
"""

import json
import os
from datetime import datetime, date
from pathlib import Path

from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
)

# ===== 設定 =====
PROPERTY_ID = "540457835"
CREDENTIALS_FILE = Path(__file__).parent / "ga4_credentials.json"
OUTPUT_DIR = Path("C:/Users/yukic/マイドライブ/アクションログ/web_analytics")

# ===== 認証 =====
credentials = service_account.Credentials.from_service_account_file(
    CREDENTIALS_FILE,
    scopes=["https://www.googleapis.com/auth/analytics.readonly"],
)
client = BetaAnalyticsDataClient(credentials=credentials)


def run_report(dimensions, metrics, date_ranges):
    request = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=date_ranges,
    )
    return client.run_report(request)


def fetch_overview(start_date, end_date):
    """全体サマリー"""
    response = run_report(
        dimensions=[],
        metrics=[
            "sessions",
            "totalUsers",
            "newUsers",
            "screenPageViews",
            "averageSessionDuration",
            "bounceRate",
        ],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )
    row = response.rows[0] if response.rows else None
    if not row:
        return {}
    values = [v.value for v in row.metric_values]
    return {
        "sessions": int(values[0]),
        "total_users": int(values[1]),
        "new_users": int(values[2]),
        "page_views": int(values[3]),
        "avg_session_duration_sec": float(values[4]),
        "bounce_rate": float(values[5]),
    }


def fetch_top_pages(start_date, end_date, limit=10):
    """人気ページ"""
    response = run_report(
        dimensions=["pagePath", "pageTitle"],
        metrics=["screenPageViews", "averageSessionDuration"],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )
    pages = []
    for row in response.rows[:limit]:
        dims = [d.value for d in row.dimension_values]
        vals = [v.value for v in row.metric_values]
        pages.append({
            "path": dims[0],
            "title": dims[1],
            "views": int(vals[0]),
            "avg_duration_sec": float(vals[1]),
        })
    return sorted(pages, key=lambda x: x["views"], reverse=True)


def fetch_traffic_sources(start_date, end_date):
    """流入元"""
    response = run_report(
        dimensions=["sessionDefaultChannelGroup"],
        metrics=["sessions", "totalUsers"],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )
    sources = []
    for row in response.rows:
        dims = [d.value for d in row.dimension_values]
        vals = [v.value for v in row.metric_values]
        sources.append({
            "channel": dims[0],
            "sessions": int(vals[0]),
            "users": int(vals[1]),
        })
    return sorted(sources, key=lambda x: x["sessions"], reverse=True)


def fetch_devices(start_date, end_date):
    """デバイス"""
    response = run_report(
        dimensions=["deviceCategory"],
        metrics=["sessions"],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )
    devices = []
    for row in response.rows:
        dims = [d.value for d in row.dimension_values]
        vals = [v.value for v in row.metric_values]
        devices.append({"device": dims[0], "sessions": int(vals[0])})
    return sorted(devices, key=lambda x: x["sessions"], reverse=True)


def sec_to_mmss(sec):
    sec = int(float(sec))
    return f"{sec // 60}分{sec % 60}秒"


def generate_markdown(year_month: str):
    """
    year_month: "2026-06" 形式
    """
    y, m = year_month.split("-")
    start_date = f"{y}-{m}-01"
    # 月末日を計算
    if int(m) == 12:
        end_date = f"{y}-12-31"
    else:
        import calendar
        last_day = calendar.monthrange(int(y), int(m))[1]
        end_date = f"{y}-{m}-{last_day:02d}"

    today = date.today().isoformat()

    print(f"データ取得中: {start_date} 〜 {end_date}")

    overview = fetch_overview(start_date, end_date)
    pages = fetch_top_pages(start_date, end_date)
    sources = fetch_traffic_sources(start_date, end_date)
    devices = fetch_devices(start_date, end_date)

    # セッション合計でパーセント計算
    total_sessions = sum(s["sessions"] for s in sources) or 1
    total_device_sessions = sum(d["sessions"] for d in devices) or 1

    sessions    = overview.get('sessions', 0) or 0
    total_users = overview.get('total_users', 0) or 0
    new_users   = overview.get('new_users', 0) or 0
    page_views  = overview.get('page_views', 0) or 0
    avg_dur     = overview.get('avg_session_duration_sec', 0) or 0
    bounce      = overview.get('bounce_rate', 0) or 0

    md = f"""# 意思決定株式会社 Web アナリティクス — {year_month}

取得日: {today}
対象期間: {start_date} 〜 {end_date}
対象URL: https://ontology-incubation.netlify.app

---

## サマリー

| 指標 | 値 |
|------|----|
| セッション数 | {int(sessions):,} |
| ユーザー数（総計） | {int(total_users):,} |
| 新規ユーザー | {int(new_users):,} |
| ページビュー | {int(page_views):,} |
| 平均セッション時間 | {sec_to_mmss(avg_dur)} |
| 直帰率 | {float(bounce) * 100:.1f}% |

---

## 流入チャネル

| チャネル | セッション | 割合 |
|----------|------------|------|
"""
    for s in sources:
        pct = s["sessions"] / total_sessions * 100
        md += f"| {s['channel']} | {s['sessions']:,} | {pct:.1f}% |\n"

    md += f"""
---

## 人気ページ（上位{len(pages)}件）

| ページ | PV | 平均滞在時間 |
|--------|----|------------|
"""
    for p in pages:
        md += f"| {p['path']} | {p['views']:,} | {sec_to_mmss(p['avg_duration_sec'])} |\n"

    md += """
---

## デバイス

| デバイス | セッション | 割合 |
|----------|------------|------|
"""
    for d in devices:
        pct = d["sessions"] / total_device_sessions * 100
        md += f"| {d['device']} | {d['sessions']:,} | {pct:.1f}% |\n"

    md += f"""
---

## Claude向けメモ

- このファイルは fetch_analytics.py により自動生成されている
- 次回取得: 来月1日以降に `python fetch_analytics.py` を実行
- 気になる変化があればアクションログに記録すること
"""
    return md


def main():
    # 実行月を自動判定（当月）
    today = date.today()
    year_month = today.strftime("%Y-%m")

    # 出力ディレクトリ作成
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{year_month}_web_analytics.md"

    print(f"=== GA4 アナリティクス取得 ===")
    print(f"プロパティID: {PROPERTY_ID}")
    print(f"対象月: {year_month}")
    print(f"出力先: {output_file}")
    print()

    md = generate_markdown(year_month)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"[完了] {output_file}")
    print()
    print("--- プレビュー（先頭30行）---")
    for line in md.splitlines()[:30]:
        print(line)


if __name__ == "__main__":
    main()
