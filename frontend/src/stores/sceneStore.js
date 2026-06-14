/**
 * 场景模式状态管理
 * 支持手动切换和 AI 自动切换
 */
import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

const STORAGE_KEY = 'starvisionchat_scene'

// 场景模式定义
const SCENE_MODES = {
  companion: {
    id: 'companion',
    name: '陪伴模式',
    icon: 'ChatDotRound',
    color: '#E85D2A',
    description: '轻松聊天，情感陪伴',
    systemPrompt: `你是用户的好朋友，一个温暖、善解人意的 AI 陪伴者。
你的任务是陪用户聊天、倾听他们的心事、给予情感支持。
回复风格：温暖、亲切、口语化，适当使用表情。
如果用户看起来开心，一起分享快乐；如果用户看起来难过，给予安慰和鼓励。
关注用户的情绪变化，主动关心他们的感受。`,
    autoSwitchHints: ['无聊', '难过', '开心', '聊聊', '陪我', '心情', '烦'],
  },
  interview: {
    id: 'interview',
    name: '模拟面试',
    icon: 'User',
    color: '#3B7DD8',
    description: '面试辅导，提升技巧',
    systemPrompt: `你是一位专业的面试辅导教练。
你的任务是帮助用户准备面试，包括：
1. 回答常见的面试问题
2. 提供回答思路和技巧
3. 指出用户回答中的优点和改进空间
4. 模拟真实面试场景进行练习
回复风格：专业、有条理、建设性反馈。
如果用户展示了简历或面试题目，仔细分析并给出针对性建议。`,
    autoSwitchHints: ['面试', '简历', '求职', '工作', '应聘', '自我介绍'],
  },
  health: {
    id: 'health',
    name: '健康模式',
    icon: 'FirstAidKit',
    color: '#4A8C5C',
    description: '健康咨询，生活建议',
    systemPrompt: `你是一位健康生活顾问（注意：你不是医生，不能提供医疗诊断）。
你的任务是：
1. 提供健康生活方式建议
2. 解答常见的健康知识问题
3. 如果用户展示了食物，分析营养成分
4. 如果用户展示了运动场景，给予运动建议
5. 提醒用户注意休息和作息
回复风格：关心、专业、有科学依据。
重要提示：如果用户描述了严重症状，务必建议他们及时就医，不要自行诊断。`,
    autoSwitchHints: ['健康', '运动', '饮食', '减肥', '睡眠', '不舒服', '头疼', '累'],
  },
  learning: {
    id: 'learning',
    name: '学习辅导',
    icon: 'Reading',
    color: '#FF9E7B',
    description: '知识学习，题目解答',
    systemPrompt: `你是一位耐心的学习辅导老师。
你的任务是：
1. 帮助用户理解知识点
2. 解答学习中的疑问
3. 如果用户展示了题目，先引导思考，再给出答案
4. 用简单易懂的方式解释复杂概念
5. 鼓励用户独立思考
回复风格：耐心、循序渐进、启发式教学。
教学方法：先问用户哪里不懂，然后从基础开始讲解，最后举一反三。`,
    autoSwitchHints: ['学习', '题目', '怎么做', '为什么', '解释', '不懂', '公式', '作业'],
  },
  rest: {
    id: 'rest',
    name: '休息模式',
    icon: 'Moon',
    color: '#7B9AFF',
    description: '放松身心，助眠冥想',
    systemPrompt: `你是一位放松引导师，帮助用户休息和放松。
你的任务是：
1. 引导用户进行深呼吸和冥想
2. 讲述轻松的故事或自然场景描述
3. 播放舒缓的背景音建议
4. 帮助用户缓解压力和焦虑
5. 如果用户看起来疲惫，建议他们休息
回复风格：轻柔、缓慢、治愈。
语调：像夜晚的轻声细语，让人感到安心和平静。`,
    autoSwitchHints: ['休息', '睡觉', '失眠', '放松', '冥想', '压力', '焦虑', '累'],
  },
}

// 场景顺序（用于 UI 显示）
const SCENE_ORDER = ['companion', 'interview', 'health', 'learning', 'rest']
const CUSTOM_SCENES_KEY = 'starvisionchat_custom_scenes'

function loadScene() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      // 支持内置场景和自定义场景
      if (SCENE_MODES[parsed] || loadCustomScenes().some(s => s.id === parsed)) {
        return parsed
      }
    }
  } catch { /* ignore */ }
  return 'companion'
}

function loadCustomScenes() {
  try {
    const saved = localStorage.getItem(CUSTOM_SCENES_KEY)
    return saved ? JSON.parse(saved) : []
  } catch { return [] }
}

function saveCustomScenes(scenes) {
  try {
    localStorage.setItem(CUSTOM_SCENES_KEY, JSON.stringify(scenes))
  } catch { /* ignore */ }
}

export const useSceneStore = defineStore('scene', () => {
  const currentSceneId = ref(loadScene())
  const customScenes = ref(loadCustomScenes())
  const isAutoSwitchEnabled = ref(true)

  // 查找场景（内置 + 自定义）
  function findScene(id) {
    return SCENE_MODES[id] || customScenes.value.find(s => s.id === id)
  }

  // 当前场景配置
  const currentScene = computed(() => findScene(currentSceneId.value) || SCENE_MODES.companion)

  // 所有场景列表（内置 + 自定义）
  const scenes = computed(() => {
    const builtIn = SCENE_ORDER.map(id => SCENE_MODES[id])
    return [...builtIn, ...customScenes.value]
  })

  // 当前系统提示词
  const systemPrompt = computed(() => currentScene.value.systemPrompt)

  // 持久化
  watch(currentSceneId, (val) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(val))
    } catch { /* ignore */ }
  })

  /**
   * 手动切换场景
   */
  function switchScene(sceneId) {
    const scene = findScene(sceneId)
    if (scene) {
      currentSceneId.value = sceneId
      console.log(`场景切换: ${scene.name}`)
    }
  }

  /**
   * 添加自定义场景
   */
  function addCustomScene(name, systemPrompt) {
    const id = 'custom_' + Date.now()
    const scene = {
      id,
      name,
      icon: 'Star',
      color: '#E85D2A',
      description: name,
      systemPrompt,
      isCustom: true,
    }
    customScenes.value.push(scene)
    saveCustomScenes(customScenes.value)
    return id
  }

  /**
   * 删除自定义场景
   */
  function removeCustomScene(sceneId) {
    customScenes.value = customScenes.value.filter(s => s.id !== sceneId)
    saveCustomScenes(customScenes.value)
    // 如果当前场景被删除，切回陪伴模式
    if (currentSceneId.value === sceneId) {
      switchScene('companion')
    }
  }

  /**
   * 根据用户输入自动判断是否需要切换场景
   * 返回建议的场景 ID，如果没有匹配返回 null
   */
  function detectScene(userText) {
    if (!isAutoSwitchEnabled.value) return null

    const text = userText.toLowerCase()

    // 检查每个场景的关键词
    for (const sceneId of SCENE_ORDER) {
      const scene = SCENE_MODES[sceneId]
      if (scene.autoSwitchHints.some(hint => text.includes(hint))) {
        // 如果当前不在这个场景，返回建议
        if (currentSceneId.value !== sceneId) {
          return sceneId
        }
      }
    }

    return null
  }

  /**
   * 根据视觉内容自动判断场景
   * 返回建议的场景 ID
   */
  function detectSceneFromVision(imageDescription) {
    if (!isAutoSwitchEnabled.value || !imageDescription) return null

    const desc = imageDescription.toLowerCase()

    // 食物 → 健康模式
    if (desc.includes('食物') || desc.includes('餐') || desc.includes('水果') ||
        desc.includes('蔬菜') || desc.includes('meal') || desc.includes('food')) {
      if (currentSceneId.value !== 'health') return 'health'
    }

    // 书本/题目 → 学习模式
    if (desc.includes('书') || desc.includes('题') || desc.includes('公式') ||
        desc.includes('作业') || desc.includes('book') || desc.includes('homework')) {
      if (currentSceneId.value !== 'learning') return 'learning'
    }

    // 简历/办公 → 面试模式
    if (desc.includes('简历') || desc.includes('办公') || desc.includes('电脑屏幕') ||
        desc.includes('resume') || desc.includes('office')) {
      if (currentSceneId.value !== 'interview') return 'interview'
    }

    // 睡床/夜晚 → 休息模式
    if (desc.includes('床') || desc.includes('枕头') || desc.includes('夜晚') ||
        desc.includes('bed') || desc.includes('night')) {
      if (currentSceneId.value !== 'rest') return 'rest'
    }

    return null
  }

  return {
    currentSceneId,
    currentScene,
    scenes,
    customScenes,
    systemPrompt,
    isAutoSwitchEnabled,
    switchScene,
    addCustomScene,
    removeCustomScene,
    detectScene,
    detectSceneFromVision,
  }
})

export { SCENE_MODES, SCENE_ORDER }
