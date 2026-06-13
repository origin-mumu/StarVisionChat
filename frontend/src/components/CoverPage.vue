<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const emit = defineEmits(['enter'])

/* ─── Particle canvas ─── */
const canvasRef = ref(null)
const isVisible = ref(false)
let animId = 0

const PARTICLE_COUNT = 120
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
    this.speedX = (Math.random() - 0.5) * 0.3
    this.speedY = (Math.random() - 0.5) * 0.3
    this.opacity = Math.random() * 0.5 + 0.1
    this.pulse = Math.random() * 0.005 + 0.002
    this.phase = Math.random() * Math.PI * 2
  }
  update(time) {
    this.x += this.speedX
    this.y += this.speedY
    if (this.x < 0 || this.x > width) this.speedX *= -1
    if (this.y < 0 || this.y > height) this.speedY *= -1
    this.opacity = 0.15 + Math.sin(time * this.pulse + this.phase) * 0.15
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

  // Draw connecting lines between nearby particles
  ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#E85D2A'
  ctx.lineWidth = 0.3
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x
      const dy = particles[i].y - particles[j].y
      const dist = Math.sqrt(dx * dx + dy * dy)
      if (dist < 120) {
        ctx.globalAlpha = (1 - dist / 120) * 0.08
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
  setTimeout(() => emit('enter'), 400)
}

onMounted(() => {
  resize()
  particles = Array.from({ length: PARTICLE_COUNT }, () => new CoverParticle())
  window.addEventListener('resize', resize)
  animId = requestAnimationFrame(animate)
  // Fade in
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

    <div class="cover-content">
      <!-- Logo / Brand -->
      <div class="cover-logo">
        <div class="logo-glow"></div>
        <svg class="logo-icon" viewBox="0 0 48 48" fill="none">
          <circle cx="24" cy="24" r="20" stroke="currentColor" stroke-width="1.5" opacity="0.3" />
          <circle cx="24" cy="24" r="12" stroke="currentColor" stroke-width="1.5" opacity="0.5" />
          <circle cx="24" cy="24" r="4" fill="currentColor" />
          <path d="M24 4 L26 10 L24 8 L22 10 Z" fill="currentColor" opacity="0.6" />
          <path d="M24 44 L26 38 L24 40 L22 38 Z" fill="currentColor" opacity="0.6" />
          <path d="M4 24 L10 22 L8 24 L10 26 Z" fill="currentColor" opacity="0.6" />
          <path d="M44 24 L38 22 L40 24 L38 26 Z" fill="currentColor" opacity="0.6" />
        </svg>
      </div>

      <h1 class="cover-title">StarVision</h1>
      <p class="cover-subtitle">AI 视觉对话助手</p>
      <p class="cover-desc">融合视觉感知与自然语言，开启智能对话新体验</p>

      <button class="cover-btn" @click="handleEnter">
        <span>开始体验</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M5 12h14M12 5l7 7-7 7" />
        </svg>
      </button>
    </div>

    <div class="cover-footer">
      <span>Powered by GPT-4o & Whisper</span>
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
    radial-gradient(circle at 30% 40%, var(--orb-1) 0%, transparent 50%),
    radial-gradient(circle at 70% 60%, var(--orb-2) 0%, transparent 50%);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.4s ease;
}
.cover.visible {
  opacity: 1;
}

.cover-canvas {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.cover-content {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  animation: cover-rise 0.8s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  animation-delay: 0.2s;
}

@keyframes cover-rise {
  from { opacity: 0; transform: translateY(30px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.cover-logo {
  position: relative;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
}

.logo-glow {
  position: absolute;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: var(--accent);
  filter: blur(60px);
  opacity: 0.15;
  animation: logo-pulse 3s ease-in-out infinite;
}

@keyframes logo-pulse {
  0%, 100% { opacity: 0.1; transform: scale(1); }
  50% { opacity: 0.2; transform: scale(1.1); }
}

.logo-icon {
  width: 64px;
  height: 64px;
  animation: logo-spin 20s linear infinite;
}

@keyframes logo-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.cover-title {
  font-size: clamp(2rem, 5vw, 3rem);
  font-weight: 800;
  letter-spacing: 0.08em;
  color: var(--ink);
  margin: 0;
  line-height: 1.2;
}

.cover-subtitle {
  font-size: 18px;
  font-weight: 500;
  color: var(--ink-soft);
  margin: 0;
  letter-spacing: 0.15em;
}

.cover-desc {
  font-size: 14px;
  color: var(--ink-muted);
  margin: 0;
  max-width: 360px;
  text-align: center;
  line-height: 1.6;
}

.cover-btn {
  margin-top: 24px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 14px 40px;
  border-radius: 999px;
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  box-shadow: var(--shadow-button);
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  letter-spacing: 0.05em;
}
.cover-btn:hover {
  transform: translateY(-3px) scale(1.03);
  box-shadow: var(--shadow-button-hover);
}
.cover-btn:active {
  transform: translateY(0) scale(0.98);
}

.cover-footer {
  position: absolute;
  bottom: 32px;
  font-size: 12px;
  color: var(--ink-muted);
  letter-spacing: 1px;
  opacity: 0.6;
}

/* Responsive */
@media (max-width: 768px) {
  .cover-title {
    font-size: 2rem;
  }
  .cover-subtitle {
    font-size: 15px;
  }
  .cover-btn {
    padding: 12px 32px;
    font-size: 15px;
  }
}
</style>
