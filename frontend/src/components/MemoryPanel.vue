<script setup>
import { ref, onMounted } from 'vue'
import {
  Notebook,
  Checked,
  CircleCheck,
  Star,
  StarFilled,
  Delete,
  Edit,
  Search,
  Close,
  Plus,
  Refresh,
} from '@element-plus/icons-vue'

const emit = defineEmits(['close'])

const activeTab = ref('memories')
const memories = ref([])
const reminders = ref([])
const searchQuery = ref('')
const editingId = ref(null)
const editContent = ref('')

// ─── 记忆 ───

async function loadMemories() {
  try {
    const res = await fetch('/api/memory/list?limit=50')
    memories.value = await res.json()
  } catch { /* ignore */ }
}

async function searchMemories() {
  if (!searchQuery.value.trim()) return loadMemories()
  try {
    const res = await fetch(`/api/memory/search?q=${encodeURIComponent(searchQuery.value)}`)
    memories.value = await res.json()
  } catch { /* ignore */ }
}

async function toggleImportant(m) {
  try {
    await fetch(`/api/memory/update/${m.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ is_important: !m.is_important })
    })
    m.is_important = !m.is_important
  } catch { /* ignore */ }
}

async function deleteMemory(id) {
  try {
    await fetch(`/api/memory/delete/${id}`, { method: 'DELETE' })
    memories.value = memories.value.filter(m => m.id !== id)
  } catch { /* ignore */ }
}

function startEdit(m) {
  editingId.value = m.id
  editContent.value = m.content
}

async function saveEdit(m) {
  try {
    await fetch(`/api/memory/update/${m.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: editContent.value })
    })
    m.content = editContent.value
    editingId.value = null
  } catch { /* ignore */ }
}

// ─── 提醒 ───

async function loadReminders() {
  try {
    const res = await fetch('/api/memory/reminders')
    reminders.value = await res.json()
  } catch { /* ignore */ }
}

async function toggleDone(r) {
  try {
    await fetch(`/api/memory/reminders/complete/${r.id}`, { method: 'PUT' })
    r.is_done = 1
  } catch { /* ignore */ }
}

async function deleteReminder(id) {
  try {
    await fetch(`/api/memory/reminders/delete/${id}`, { method: 'DELETE' })
    reminders.value = reminders.value.filter(r => r.id !== id)
  } catch { /* ignore */ }
}

// ─── 工具函数 ───

const categoryLabels = {
  preference: '偏好',
  fact: '事实',
  event: '事件',
  todo: '待办',
}

const categoryIcons = {
  preference: Star,
  fact: Notebook,
  event: CircleCheck,
  todo: Checked,
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

onMounted(() => {
  loadMemories()
  loadReminders()
})
</script>

<template>
  <div class="memory-panel">
    <!-- 头部 -->
    <div class="panel-header">
      <div class="panel-title">
        <el-icon><Notebook /></el-icon>
        <span>AI 记忆</span>
      </div>
      <div class="header-actions">
        <el-icon class="action-btn" @click="loadMemories(); loadReminders()"><Refresh /></el-icon>
        <el-icon class="action-btn" @click="emit('close')"><Close /></el-icon>
      </div>
    </div>

    <!-- 标签页 -->
    <div class="tabs">
      <div
        class="tab"
        :class="{ active: activeTab === 'memories' }"
        @click="activeTab = 'memories'"
      >
        <el-icon><Notebook /></el-icon>记忆
      </div>
      <div
        class="tab"
        :class="{ active: activeTab === 'reminders' }"
        @click="activeTab = 'reminders'"
      >
        <el-icon><Checked /></el-icon>待办
      </div>
    </div>

    <!-- 搜索栏 -->
    <div v-if="activeTab === 'memories'" class="search-bar">
      <el-icon><Search /></el-icon>
      <input
        v-model="searchQuery"
        placeholder="搜索记忆..."
        @input="searchMemories"
      />
    </div>

    <!-- 记忆列表 -->
    <div v-if="activeTab === 'memories'" class="list-container">
      <div v-if="memories.length === 0" class="empty-state">
        <el-icon :size="48"><Notebook /></el-icon>
        <p>暂无记忆</p>
        <p class="empty-hint">对话中说"帮我记一下"即可保存</p>
      </div>
      <div v-for="m in memories" :key="m.id" class="memory-item">
        <div class="item-icon" :class="m.category">
          <el-icon><component :is="categoryIcons[m.category] || Notebook" /></el-icon>
        </div>
        <div class="item-body">
          <div v-if="editingId === m.id" class="edit-row">
            <input v-model="editContent" @keyup.enter="saveEdit(m)" />
            <el-icon class="save-btn" @click="saveEdit(m)"><CircleCheck /></el-icon>
          </div>
          <div v-else class="item-content">{{ m.content }}</div>
          <div class="item-meta">
            <span class="category-tag">{{ categoryLabels[m.category] || m.category }}</span>
            <span class="time">{{ formatTime(m.created_at) }}</span>
          </div>
        </div>
        <div class="item-actions">
          <el-icon @click="toggleImportant(m)">
            <component :is="m.is_important ? StarFilled : Star" />
          </el-icon>
          <el-icon @click="startEdit(m)"><Edit /></el-icon>
          <el-icon class="danger" @click="deleteMemory(m.id)"><Delete /></el-icon>
        </div>
      </div>
    </div>

    <!-- 提醒列表 -->
    <div v-if="activeTab === 'reminders'" class="list-container">
      <div v-if="reminders.length === 0" class="empty-state">
        <el-icon :size="48"><Checked /></el-icon>
        <p>暂无待办</p>
        <p class="empty-hint">对话中说"提醒我"即可创建</p>
      </div>
      <div
        v-for="r in reminders"
        :key="r.id"
        class="reminder-item"
        :class="{ done: r.is_done }"
      >
        <el-icon class="check-btn" @click="toggleDone(r)">
          <component :is="r.is_done ? CircleCheck : Checked" />
        </el-icon>
        <div class="reminder-body">
          <div class="reminder-content">{{ r.content }}</div>
          <div v-if="r.remind_at" class="reminder-time">{{ r.remind_at }}</div>
        </div>
        <el-icon class="danger" @click="deleteReminder(r.id)"><Delete /></el-icon>
      </div>
    </div>
  </div>
</template>

<style scoped>
.memory-panel {
  width: 340px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--glass-mid);
  backdrop-filter: blur(24px);
  border-left: 1px solid var(--border);
  font-size: 14px;
  color: var(--ink);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 12px;
  border-bottom: 1px solid var(--border);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.2s;
}
.action-btn:hover {
  opacity: 1;
}

/* Tabs */
.tabs {
  display: flex;
  border-bottom: 1px solid var(--border);
}

.tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  cursor: pointer;
  opacity: 0.5;
  transition: all 0.2s;
  border-bottom: 2px solid transparent;
}
.tab.active {
  opacity: 1;
  border-bottom-color: var(--accent);
  color: var(--accent);
}
.tab:hover {
  opacity: 0.8;
}

/* Search */
.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  opacity: 0.6;
}
.search-bar input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: var(--ink);
  font-size: 13px;
}

/* List */
.list-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 16px;
  opacity: 0.4;
}
.empty-state p {
  margin: 8px 0 0;
}
.empty-hint {
  font-size: 12px;
  opacity: 0.6;
}

/* Memory item */
.memory-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 8px;
  border-radius: 8px;
  transition: background 0.15s;
}
.memory-item:hover {
  background: var(--glass-base);
}

.item-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 14px;
}
.item-icon.preference { background: rgba(232, 168, 96, 0.15); color: var(--warm); }
.item-icon.fact { background: var(--accent-soft); color: var(--accent); }
.item-icon.event { background: rgba(72, 201, 176, 0.15); color: #48C9B0; }
.item-icon.todo { background: rgba(123, 154, 255, 0.15); color: #7B9AFF; }

.item-body {
  flex: 1;
  min-width: 0;
}

.item-content {
  word-break: break-word;
  line-height: 1.5;
}

.edit-row {
  display: flex;
  gap: 6px;
}
.edit-row input {
  flex: 1;
  background: var(--glass-base);
  border: 1px solid var(--border-focus);
  border-radius: 4px;
  padding: 2px 6px;
  color: var(--ink);
  font-size: 13px;
  outline: none;
}
.save-btn {
  cursor: pointer;
  color: var(--accent);
}

.item-meta {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  font-size: 11px;
  opacity: 0.5;
}

.category-tag {
  background: var(--glass-base);
  padding: 1px 6px;
  border-radius: 4px;
}

.item-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s;
  flex-shrink: 0;
}
.memory-item:hover .item-actions {
  opacity: 0.6;
}
.item-actions .el-icon {
  cursor: pointer;
  font-size: 14px;
}
.item-actions .el-icon:hover {
  opacity: 1;
}
.item-actions .danger:hover {
  color: #e74c3c;
}

/* Reminder item */
.reminder-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 8px;
  border-radius: 8px;
  transition: background 0.15s;
}
.reminder-item:hover {
  background: var(--glass-base);
}
.reminder-item.done {
  opacity: 0.4;
}
.reminder-item.done .reminder-content {
  text-decoration: line-through;
}

.check-btn {
  cursor: pointer;
  font-size: 18px;
  color: var(--accent);
  flex-shrink: 0;
}

.reminder-body {
  flex: 1;
  min-width: 0;
}
.reminder-content {
  word-break: break-word;
}
.reminder-time {
  font-size: 11px;
  opacity: 0.5;
  margin-top: 2px;
}
</style>
