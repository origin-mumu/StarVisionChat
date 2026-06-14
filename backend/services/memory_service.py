"""
记忆服务
使用 SQLite 存储用户记忆、偏好、待办提醒
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from ..config import settings

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.db")


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL DEFAULT 'fact',
                content TEXT NOT NULL,
                tags TEXT DEFAULT '',
                is_important INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                remind_at TEXT,
                is_done INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
            CREATE INDEX IF NOT EXISTS idx_reminders_done ON reminders(is_done);
        """)
        conn.commit()
    finally:
        conn.close()


# ─── 记忆 CRUD ───

def save_memory(content: str, category: str = "fact", tags: str = "", is_important: bool = False) -> Dict[str, Any]:
    """保存一条记忆"""
    now = datetime.now().isoformat()
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO memories (category, content, tags, is_important, created_at, updated_at) VALUES (?,?,?,?,?,?)",
            (category, content, tags, int(is_important), now, now)
        )
        conn.commit()
        return {"id": cursor.lastrowid, "category": category, "content": content, "tags": tags, "is_important": is_important}
    finally:
        conn.close()


def get_memories(category: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """获取记忆列表"""
    conn = get_db()
    try:
        if category:
            rows = conn.execute(
                "SELECT * FROM memories WHERE category=? ORDER BY is_important DESC, updated_at DESC LIMIT ?",
                (category, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY is_important DESC, updated_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def search_memories(keyword: str) -> List[Dict[str, Any]]:
    """搜索记忆"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM memories WHERE content LIKE ? OR tags LIKE ? ORDER BY is_important DESC, updated_at DESC LIMIT 20",
            (f"%{keyword}%", f"%{keyword}%")
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_memory(memory_id: int, content: str = None, category: str = None, tags: str = None, is_important: bool = None) -> bool:
    """更新记忆"""
    conn = get_db()
    try:
        fields = []
        values = []
        if content is not None:
            fields.append("content=?")
            values.append(content)
        if category is not None:
            fields.append("category=?")
            values.append(category)
        if tags is not None:
            fields.append("tags=?")
            values.append(tags)
        if is_important is not None:
            fields.append("is_important=?")
            values.append(int(is_important))
        if not fields:
            return False
        fields.append("updated_at=?")
        values.append(datetime.now().isoformat())
        values.append(memory_id)
        conn.execute(f"UPDATE memories SET {','.join(fields)} WHERE id=?", values)
        conn.commit()
        return True
    finally:
        conn.close()


def delete_memory(memory_id: int) -> bool:
    """删除记忆"""
    conn = get_db()
    try:
        conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
        conn.commit()
        return True
    finally:
        conn.close()


# ─── 待办/提醒 CRUD ───

def create_reminder(content: str, remind_at: Optional[str] = None) -> Dict[str, Any]:
    """创建提醒"""
    now = datetime.now().isoformat()
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO reminders (content, remind_at, is_done, created_at) VALUES (?,?,0,?)",
            (content, remind_at, now)
        )
        conn.commit()
        return {"id": cursor.lastrowid, "content": content, "remind_at": remind_at, "is_done": False}
    finally:
        conn.close()


def get_reminders(is_done: Optional[bool] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """获取提醒列表"""
    conn = get_db()
    try:
        if is_done is not None:
            rows = conn.execute(
                "SELECT * FROM reminders WHERE is_done=? ORDER BY remind_at ASC NULLS LAST LIMIT ?",
                (int(is_done), limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM reminders ORDER BY is_done ASC, remind_at ASC NULLS LAST LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def complete_reminder(reminder_id: int) -> bool:
    """标记提醒完成"""
    conn = get_db()
    try:
        conn.execute("UPDATE reminders SET is_done=1 WHERE id=?", (reminder_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def delete_reminder(reminder_id: int) -> bool:
    """删除提醒"""
    conn = get_db()
    try:
        conn.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
        conn.commit()
        return True
    finally:
        conn.close()


# ─── 上下文注入 ───

def get_memory_context(limit: int = 10) -> str:
    """获取记忆上下文，注入到 system prompt"""
    memories = get_memories(limit=limit)
    reminders = get_reminders(is_done=False, limit=5)
    if not memories and not reminders:
        return ""

    parts = []
    if memories:
        items = []
        for m in memories:
            prefix = "[!] " if m["is_important"] else ""
            items.append(f"{prefix}{m['content']}")
        parts.append("用户记忆:\n" + "\n".join(f"- {i}" for i in items))

    if reminders:
        items = []
        for r in reminders:
            time_str = f" ({r['remind_at']})" if r["remind_at"] else ""
            items.append(f"{r['content']}{time_str}")
        parts.append("待办提醒:\n" + "\n".join(f"- {i}" for i in items))

    return "\n\n".join(parts)


# 启动时初始化数据库
init_db()
