"""
微信推送服务（Server酱）
- 高影响事件自动推送到微信
- 支持 Markdown 格式的详细分析报告
"""
import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SERVERCHAN_API = "https://sctapi.ftqq.com/{key}.send"


async def send_wechat(title: str, content: str = "") -> bool:
    """
    通过 Server酱 发送微信消息
    - title: 消息标题（最多 32 字）
    - content: 消息正文（支持 Markdown）
    """
    if not settings.WECHAT_SENDKEY:
        logger.warning("[Notifier] WECHAT_SENDKEY 未配置，跳过推送")
        return False

    url = SERVERCHAN_API.format(key=settings.WECHAT_SENDKEY)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, data={
                "title": title[:32],
                "desp": content,
            })
            result = resp.json()

            if result.get("code") == 0:
                logger.info(f"[Notifier] ✅ 微信推送成功: {title}")
                return True
            else:
                logger.error(f"[Notifier] ❌ 微信推送失败: {result}")
                return False

    except Exception as e:
        logger.error(f"[Notifier] ❌ 推送异常: {e}")
        return False


def format_analysis_message(analysis_data: dict) -> tuple[str, str]:
    """
    将分析结果格式化为微信推送的标题和正文
    返回 (title, markdown_content)
    """
    ticker = analysis_data.get("ticker", "???")
    sentiment = analysis_data.get("sentiment", "neutral")
    impact = analysis_data.get("impact_level", "low")
    news_title = analysis_data.get("news_title", "")
    summary_cn = analysis_data.get("summary_cn", "")
    confidence = analysis_data.get("confidence", 0)

    # 情感 emoji
    emoji = {"bullish": "🟢📈", "bearish": "🔴📉", "neutral": "⚪➖"}.get(sentiment, "❓")
    sentiment_cn = {"bullish": "利好", "bearish": "利空", "neutral": "中性"}.get(sentiment, sentiment)

    # 标题（最多 32 字）
    title = f"{emoji} {ticker} | {sentiment_cn} | {news_title[:15]}"

    # 正文 Markdown
    lines = [
        f"## {emoji} {ticker} — {sentiment_cn}信号",
        "",
        f"**新闻标题:** {news_title}",
        "",
        f"**AI 摘要:** {summary_cn}",
        "",
        f"| 指标 | 值 |",
        f"|:---|:---|",
        f"| 情感判定 | {sentiment_cn} {emoji} |",
        f"| 置信度 | {confidence * 100:.0f}% |",
        f"| 影响级别 | {'⚡ HIGH' if impact == 'high' else '🔶 MEDIUM' if impact == 'medium' else '▫️ LOW'} |",
        f"| 影响时长 | {analysis_data.get('impact_duration', '—')} |",
    ]

    # 深度分析
    da = analysis_data.get("detailed_analysis")
    if da:
        lines.append("")
        lines.append("---")
        lines.append("### 📊 深度分析")
        if da.get("direct_impact"):
            lines.append(f"**直接影响:** {da['direct_impact']}")
        if da.get("pipeline_impact"):
            lines.append(f"**管线影响:** {da['pipeline_impact']}")
        if da.get("competitive_landscape"):
            lines.append(f"**竞争格局:** {da['competitive_landscape']}")
        if da.get("revenue_impact"):
            lines.append(f"**营收影响:** {da['revenue_impact']}")
        if da.get("risk_factors"):
            lines.append("")
            lines.append("**⚠️ 风险因素:**")
            for r in da["risk_factors"]:
                lines.append(f"- {r}")

    # 关联股票
    related = analysis_data.get("related_tickers")
    if related:
        lines.append("")
        lines.append(f"**关联股票:** {', '.join(related)}")

    # 关注日期
    dates = analysis_data.get("key_dates")
    if dates:
        lines.append("")
        lines.append("**📅 后续关注:**")
        for d in dates:
            lines.append(f"- {d}")

    lines.append("")
    lines.append("---")
    lines.append("*由 StockNewsAI 自动生成*")

    return title, "\n".join(lines)


async def notify_high_impact(analysis_data: dict) -> bool:
    """
    推送高影响事件到微信
    仅在 impact_level == 'high' 时调用
    """
    title, content = format_analysis_message(analysis_data)
    return await send_wechat(title, content)
