<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import {
  View,
  Microphone,
  Connection,
  Switch,
  Notebook,
  DataAnalysis,
} from '@element-plus/icons-vue'

const router = useRouter()

/* ─── Feature cards data ─── */
const features = [
  {
    icon: View,
    title: '实时视觉感知',
    desc: '摄像头实时捕捉画面，AI 即时理解眼前的一切，所见即所得。',
  },
  {
    icon: Microphone,
    title: '语音自然对话',
    desc: '支持语音输入与 TTS 播报，无需打字，解放双手自由交流。',
  },
  {
    icon: Connection,
    title: '场景智能识别',
    desc: '多场景模式自动切换，从做饭助手到学习陪伴，AI 随境而变。',
  },
  {
    icon: Switch,
    title: '多模型自由切换',
    desc: '支持 MiMo 与 Qwen 双引擎，按需选择最合适的视觉语言模型。',
  },
  {
    icon: Notebook,
    title: '持久记忆系统',
    desc: 'AI 记住重要信息与对话上下文，越用越懂你，体验持续升级。',
  },
  {
    icon: DataAnalysis,
    title: '用量一目了然',
    desc: 'API 调用次数、Token 消耗、费用估算实时透明，心中有数。',
  },
]

/* ─── Particle canvas ─── */
const canvasRef = ref(null)
const isVisible = ref(false)
let animId = 0

const PARTICLE_COUNT = 100
let particles = []
let width = 0
let height = 0

class CoverParticle {
  constructor() {
    this.reset()
  }
  reset() {
    this.x = Math.random() * width
    this.y = Math.random() * height
    this.size = Math.random() * 2 + 0.5
    this.speedX = (Math.random() - 0.5) * 0.25
    this.speedY = (Math.random() - 0.5) * 0.25
    this.opacity = Math.random() * 0.5 + 0.1
    this.pulse = Math.random() * 0.004 + 0.001
    this.phase = Math.random() * Math.PI * 2
    this.baseX = this.x
    this.baseY = this.y
  }
  update(time) {
    this.x = this.baseX + Math.sin(time * this.pulse + this.phase) * 30
    this.y = this.baseY + Math.cos(time * this.pulse * 0.7 + this.phase) * 30
    if (this.x < 0) this.x = width
    if (this.x > width) this.x = 0
    if (this.y < 0) this.y = height
    if (this.y > height) this.y = 0
    this.opacity = 0.12 + Math.sin(time * this.pulse + this.phase) * 0.12
  }
  draw(ctx) {
    ctx.globalAlpha = this.opacity
    ctx.beginPath()
    ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2)
    ctx.fill()
  }
}

function resize() {
  const c = canvasRef.value
  if (!c) return
  width = window.innerWidth
  height = window.innerHeight
  c.width = width
  c.height = height
}

function animate(time) {
  const c = canvasRef.value
  if (!c) return
  const ctx = c.getContext('2d')
  if (!ctx) return

  ctx.clearRect(0, 0, width, height)
  ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--ink-muted').trim() || '#8A7E74'

  for (const p of particles) {
    p.update(time)
    p.draw(ctx)
  }

  // Connecting lines
  ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#E85D2A'
  ctx.lineWidth = 0.25
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x
      const dy = particles[i].y - particles[j].y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 130) {
        ctx.globalAlpha = (1 - dist / 130) * 0.06
        ctx.beginPath()
        ctx.moveTo(particles[i].x, particles[i].y)
        ctx.lineTo(particles[j].x, particles[j].y)
        ctx.stroke()
      }
    }
  }

  animId = requestAnimationFrame(animate)
}

function handleEnter() {
  isVisible.value = false
  const saved = localStorage.getItem('starvisionchat_config')
  const target = (saved && (() => {
    try {
      const config = JSON.parse(saved)
      return config.configured && config.apiKey
    } catch { return false }
  })()) ? '/chat' : '/config'
  setTimeout(() => router.push(target), 400)
}

onMounted(() => {
  resize()
  particles = Array.from({ length: PARTICLE_COUNT }, () => new CoverParticle())
  window.addEventListener('resize', resize)
  animId = requestAnimationFrame(animate)
  requestAnimationFrame(() => { isVisible.value = true })
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animId)
  window.removeEventListener('resize', resize)
})
</script>

<template>
  <div class="cover" :class="{ visible: isVisible }">
    <canvas ref="canvasRef" class="cover-canvas"></canvas>

    <div class="cover-scroll">
      <!-- ===== Hero ===== -->
      <section class="hero-section">
        <div class="cover-logo">
          <div class="logo-glow"></div>
          <div class="logo-ring">
            <svg viewBox="0 0 64 64" fill="none">
              <circle cx="32" cy="32" r="28" stroke="currentColor" stroke-width="1" opacity="0.2" />
              <circle cx="32" cy="32" r="18" stroke="currentColor" stroke-width="1.2" opacity="0.4" />
              <circle cx="32" cy="32" r="8" fill="currentColor" opacity="0.8" />
              <path d="M32 4 L34 14 L32 11 L30 14 Z" fill="currentColor" opacity="0.5" />
              <path d="M32 60 L34 50 L32 53 L30 50 Z" fill="currentColor" opacity="0.5" />
              <path d="M4 32 L14 30 L11 32 L14 34 Z" fill="currentColor" opacity="0.5" />
              <path d="M60 32 L50 30 L53 32 L50 34 Z" fill="currentColor" opacity="0.5" />
            </svg>
          </div>
        </div>

        <h1 class="hero-title">StarVision</h1>
        <p class="hero-subtitle">AI 视觉对话助手</p>
        <p class="hero-desc">融合视觉感知 · 语音交互 · 场景智能，开启下一代 AI 对话体验</p>

        <button class="hero-cta" @click="handleEnter">
          <span>开始探索</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
      </section>

      <!-- ===== Features ===== -->
      <section class="features-section">
        <h2 class="section-title">核心能力</h2>
        <div class="features-grid">
          <div
            v-for="(f, i) in features"
            :key="i"
            class="feature-card"
            :style="{ animationDelay: `${0.4 + i * 0.1}s` }"
          >
            <span class="feature-icon">
              <el-icon :size="24"><component :is="f.icon" /></el-icon>
            </span>
            <h3 class="feature-title">{{ f.title }}</h3>
            <p class="feature-desc">{{ f.desc }}</p>
          </div>
        </div>
      </section>

      <!-- ===== Bottom CTA ===== -->
      <section class="bottom-section">
        <p class="bottom-text">准备好探索 AI 视觉对话的未来了吗？</p>
        <button class="hero-cta" @click="handleEnter">
          <span>开始体验</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 12h14M12 5l7 7-7 7" />
          </svg>
        </button>
      </section>

      <footer class="cover-footer">
        <span>Powered by MiMo · Qwen &nbsp;|&nbsp; 视觉 · 语音 · 智能</span>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.cover {
  position: fixed;
  inset: 0;
  z-index: 99999;
  background-color: var(--canvas);
  background-image:
    radial-gradient(circle at 25% 20%, var(--orb-1) 0%, transparent 50%),
    radial-gradient(circle at 75% 80%, var(--orb-2) 0%, transparent 50%);
  opacity: 0;
  transition: opacity 0.5s ease;
}
.cover.visible {
  opacity: 1;
}

.cover-canvas {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.cover-scroll {
  position: relative;
  z-index: 10;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}

/* ===== Hero ===== */
.hero-section {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 20px;
  text-align: center;
}

.cover-logo {
  position: relative;
  width: 88px;
  height: 88px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
}

.logo-glow {
  position: absolute;
  width: 130px;
  height: 130px;
  border-radius: 50%;
  background: var(--accent);
  filter: blur(70px);
  opacity: 0.12;
  animation: logo-pulse 4s ease-in-out infinite;
}

@keyframes logo-pulse {
  0%, 100% { opacity: 0.08; transform: scale(1); }
  50% { opacity: 0.18; transform: scale(1.15); }
}

.logo-ring {
  position: relative;
  z-index: 1;
}

.logo-ring svg {
  width: 72px;
  height: 72px;
  animation: logo-spin 30s linear infinite;
}

@keyframes logo-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.hero-title {
  font-size: clamp(2.4rem, 6vw, 3.6rem);
  font-weight: 800;
  letter-spacing: 0.06em;
  color: var(--ink);
  margin: 0;
  line-height: 1.15;
}

.hero-subtitle {
  font-size: 18px;
  font-weight: 500;
  color: var(--accent);
  margin: 0;
  letter-spacing: 0.18em;
}

.hero-desc {
  font-size: 14px;
  color: var(--ink-muted);
  margin: 4px 0 0;
  max-width: 400px;
  line-height: 1.7;
}

.hero-cta {
  margin-top: 12px;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 15px 44px;
  border-radius: 999px;
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  box-shadow: var(--shadow-button);
  transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
  letter-spacing: 0.06em;
}
.hero-cta:hover {
  transform: translateY(-3px) scale(1.04);
  box-shadow: var(--shadow-button-hover);
}
.hero-cta:active {
  transform: translateY(0) scale(0.97);
}

/* ===== Features ===== */
.features-section {
  padding: 0 24px 80px;
  max-width: 960px;
  margin: 0 auto;
}

.section-title {
  text-align: center;
  font-size: 22px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 40px;
  letter-spacing: 0.06em;
  animation: feature-rise 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  animation-delay: 0.3s;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.feature-card {
  background: var(--glass-mid);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 0.5px solid var(--glass-border);
  border-radius: 16px;
  padding: 28px 24px;
  text-align: center;
  transition: all 0.3s ease;
  opacity: 0;
  transform: translateY(24px);
  animation: feature-rise 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
}

@keyframes feature-rise {
  from { opacity: 0; transform: translateY(24px); }
  to { opacity: 1; transform: translateY(0); }
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-card-hover);
  border-color: var(--accent);
}

.feature-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: var(--accent-soft);
  color: var(--accent);
  margin-bottom: 18px;
}

.feature-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
  margin: 0 0 8px;
  letter-spacing: 0.03em;
}

.feature-desc {
  font-size: 13px;
  color: var(--ink-muted);
  margin: 0;
  line-height: 1.7;
}

/* ===== Bottom ===== */
.bottom-section {
  text-align: center;
  padding: 0 20px 32px;
}

.bottom-text {
  font-size: 15px;
  color: var(--ink-soft);
  margin: 0 0 20px;
}

/* ===== Footer ===== */
.cover-footer {
  text-align: center;
  padding: 0 20px 36px;
  font-size: 12px;
  color: var(--ink-muted);
  letter-spacing: 0.8px;
  opacity: 0.5;
}

/* ===== Responsive ===== */
@media (max-width: 768px) {
  .hero-title {
    font-size: 2rem;
  }
  .hero-subtitle {
    font-size: 15px;
  }
  .hero-cta {
    padding: 13px 36px;
    font-size: 15px;
  }

  .features-grid {
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .feature-card {
    padding: 22px 20px;
  }

  .section-title {
    font-size: 18px;
    margin-bottom: 28px;
  }
}
</style>
