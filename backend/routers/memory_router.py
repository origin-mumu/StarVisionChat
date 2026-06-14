"""
记忆管理 REST API
提供记忆和待办的 CRUD 接口
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..services import memory_service

router = APIRouter(prefix="/api/memory", tags=["memory"])


# ─── 请求模型 ───

class MemoryCreate(BaseModel):
    content: str
    category: str = "fact"
    tags: str = ""
    is_important: bool = False

class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    is_important: Optional[bool] = None

class ReminderCreate(BaseModel):
    content: str
    remind_at: Optional[str] = None


# ─── 记忆接口 ───

@router.get("/list")
def list_memories(category: Optional[str] = None, limit: int = 50):
    """获取记忆列表"""
    return memory_service.get_memories(category=category, limit=limit)

@router.get("/search")
def search_memories(q: str):
    """搜索记忆"""
    return memory_service.search_memories(q)

@router.post("/create")
def create_memory(body: MemoryCreate):
    """创建记忆"""
    return memory_service.save_memory(
        content=body.content,
        category=body.category,
        tags=body.tags,
        is_important=body.is_important
    )

@router.put("/update/{memory_id}")
def update_memory(memory_id: int, body: MemoryUpdate):
    """更新记忆"""
    ok = memory_service.update_memory(
        memory_id,
        content=body.content,
        category=body.category,
        tags=body.tags,
        is_important=body.is_important
    )
    if not ok:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"success": True}

@router.delete("/delete/{memory_id}")
def delete_memory(memory_id: int):
    """删除记忆"""
    memory_service.delete_memory(memory_id)
    return {"success": True}


# ─── 提醒接口 ───

@router.get("/reminders")
def list_reminders(is_done: Optional[bool] = None, limit: int = 50):
    """获取提醒列表"""
    return memory_service.get_reminders(is_done=is_done, limit=limit)

@router.post("/reminders/create")
def create_reminder(body: ReminderCreate):
    """创建提醒"""
    return memory_service.create_reminder(content=body.content, remind_at=body.remind_at)

@router.put("/reminders/complete/{reminder_id}")
def complete_reminder(reminder_id: int):
    """标记提醒完成"""
    memory_service.complete_reminder(reminder_id)
    return {"success": True}

@router.delete("/reminders/delete/{reminder_id}")
def delete_reminder(reminder_id: int):
    """删除提醒"""
    memory_service.delete_reminder(reminder_id)
    return {"success": True}
