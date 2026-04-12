"""
推送通知 API
- 测试微信推送
- 查看推送配置状态
"""
from fastapi import APIRouter

from app.config import settings
from app.services.notifier import send_wechat

router = APIRouter(prefix="/notify", tags=["Notify"])


@router.get("/status")
async def notify_status():
    """查看推送配置状态"""
    return {
        "wechat": {
            "enabled": bool(settings.WECHAT_SENDKEY),
            "sendkey_preview": settings.WECHAT_SENDKEY[:8] + "..." if settings.WECHAT_SENDKEY else None,
        }
    }


@router.post("/test")
async def test_notification():
    """发送测试推送到微信"""
    title = "🧪 StockNewsAI 测试推送"
    content = """## ✅ 推送测试成功！

**恭喜，你的微信推送已配置成功。**

当系统检测到以下事件时，会自动推送到你的微信：
- ⚡ FDA 审批结果
- 🧪 Phase 3 临床试验数据
- 💊 重大药物安全事件
- 🤝 大型并购/合作协议

---
*由 StockNewsAI 自动生成*"""

    success = await send_wechat(title, content)
    return {
        "success": success,
        "message": "推送成功，请检查微信！" if success else "推送失败，请检查 SendKey",
    }
