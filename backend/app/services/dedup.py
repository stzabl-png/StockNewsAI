"""
新闻去重服务 — 基于 Redis 的指纹比对
- 使用 SHA-256 生成新闻指纹
- Redis SET 存储已处理的指纹
- 数据库 UNIQUE 约束作为兜底保障
"""
import hashlib

REDIS_KEY = "news:fingerprints"


class DedupService:
    """新闻去重服务"""

    def __init__(self, redis):
        self.redis = redis

    async def is_duplicate(self, fingerprint: str) -> bool:
        """
        检查指纹是否已存在（即是否为重复新闻）
        - 使用 SADD 原子操作：如果元素已存在返回 0，新增返回 1
        - 返回 True 表示重复，False 表示新的
        """
        added = await self.redis.sadd(REDIS_KEY, fingerprint)
        return added == 0  # 0 = 已存在 = 重复

    async def exists(self, fingerprint: str) -> bool:
        """只检查是否存在，不添加"""
        return await self.redis.sismember(REDIS_KEY, fingerprint)

    async def get_count(self) -> int:
        """获取已存储的指纹数量"""
        return await self.redis.scard(REDIS_KEY)

    @staticmethod
    def generate_fingerprint(source: str, url: str, headline: str) -> str:
        """
        生成新闻指纹
        - 使用 source + url + headline 的组合
        - URL 是最可靠的去重依据，headline 作为补充
        """
        raw = f"{source}:{url}:{headline}".strip().lower()
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── 模块级便捷函数（供 polygon_news 等新采集器直接调用）─────────────────────

async def is_duplicate(redis, fingerprint: str) -> bool:
    """检查指纹是否已在 Redis 中（不写入）"""
    return await redis.sismember(REDIS_KEY, fingerprint)


async def mark_seen(redis, fingerprint: str, ttl: int = 604800):
    """将指纹写入 Redis，TTL 默认 7 天"""
    await redis.sadd(REDIS_KEY, fingerprint)
    await redis.expire(REDIS_KEY, ttl)
