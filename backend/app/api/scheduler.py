"""
调度器管理 API
- 查看定时任务列表和下次运行时间
- 手动触发/暂停/恢复任务
"""
from fastapi import APIRouter, HTTPException

from app.services.scheduler import (
    scheduler,
    get_jobs_info,
    job_fetch_news,
    job_analyze_pending,
    job_cleanup_old_data,
)

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])

# 任务 ID → 函数映射
JOB_FUNCTIONS = {
    "fetch_news": job_fetch_news,
    "analyze_pending": job_analyze_pending,
    "cleanup_old_data": job_cleanup_old_data,
}


@router.get("/jobs")
async def list_jobs():
    """获取所有定时任务及下次运行时间"""
    return {
        "scheduler_running": scheduler.running,
        "jobs": get_jobs_info(),
    }


@router.post("/jobs/{job_id}/trigger")
async def trigger_job(job_id: str):
    """
    手动触发一个定时任务（立即执行一次）
    不影响正常的定时调度
    """
    if job_id not in JOB_FUNCTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"任务 {job_id} 不存在。可用: {list(JOB_FUNCTIONS.keys())}",
        )

    job_fn = JOB_FUNCTIONS[job_id]
    try:
        await job_fn()
        return {"message": f"任务 {job_id} 已执行完成"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"任务执行失败: {str(e)}")


@router.post("/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    """暂停一个定时任务"""
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"任务 {job_id} 不存在")

    scheduler.pause_job(job_id)
    return {"message": f"任务 {job_id} 已暂停", "job": get_jobs_info()}


@router.post("/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    """恢复一个定时任务"""
    job = scheduler.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"任务 {job_id} 不存在")

    scheduler.resume_job(job_id)
    return {"message": f"任务 {job_id} 已恢复", "job": get_jobs_info()}
