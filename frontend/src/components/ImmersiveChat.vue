<script setup>
import {
  ref,
  reactive,
  computed,
  onMounted,
  onBeforeUnmount,
  nextTick,
  watch,
} from "vue";
import { marked } from "marked";
import hljs from "highlight.js";
import { useTTS } from "../composables/useTTS";
import { useChatStore } from "../stores/chatStore";
import { useSessionStore } from "../stores/sessionStore";
import { wsService } from "../services/wsService";
import { useCamera } from "../composables/useCamera";
import { useMicrophone } from "../composables/useMicrophone";
import { useThemeStore } from "../stores/themeStore";
import SettingsPanel from "./SettingsPanel.vue";
import { storeToRefs } from "pinia";
import {
  ChatDotRound,
  Promotion,
  Star,
  User,
  Microphone,
  Mute,
  VideoCamera,
  VideoPause,
  Loading,
  Plus,
  Delete,
  Close,
} from "@element-plus/icons-vue";

const themeStore = useThemeStore();
const { currentTheme, themes } = storeToRefs(themeStore);
const { setTheme } = themeStore;

const chatStore = useChatStore();
const sessionStore = useSessionStore();
const showSessionList = ref(false);

/* ─── Model provider ─── */
const modelProvider = ref('mimo')  // mimo / qwen
let qwenImageInterval = null  // Qwen 模式下的图像发送定时器

// Load model provider from config
function loadModelProvider() {
  const saved = localStorage.getItem('starvisionchat_config')
  if (saved) {
    try {
      const config = JSON.parse(saved)
      const newProvider = config.modelProvider || 'mimo'
      if (newProvider !== modelProvider.value) {
        modelProvider.value = newProvider
        // 切换模型时更新图像流
        updateQwenImageStream()
      }
    } catch { /* ignore */ }
  }
}

// Qwen 模式下持续发送图像帧（每秒 1 帧）
function updateQwenImageStream() {
  // 清除现有定时器
  if (qwenImageInterval) {
    clearInterval(qwenImageInterval)
    qwenImageInterval = null
  }

  // 如果是 Qwen 模式且摄像头开启，开始发送图像
  if (modelProvider.value === 'qwen' && isCameraOn.value) {
    qwenImageInterval = setInterval(() => {
      const frame = captureFrame()
      if (frame) {
        wsService.send('image_stream', { image: frame })
      }
    }, 1000)  // 每秒 1 帧
  }
}

onMounted(() => {
  loadModelProvider()

  // 监听配置更新事件（从设置面板触发）
  window.addEventListener('config-updated', loadModelProvider)
})

onBeforeUnmount(() => {
  window.removeEventListener('config-updated', loadModelProvider)
})

const {
  ttsEnabled,
  isSpeaking: isTTSSpeaking,
  toggleTTS,
  feedStreamChunk,
  flushStreamBuffer,
  reset: resetTTS,
} = useTTS();

/* ─── Camera & Mic composables ─── */
const {
  videoRef,
  isStreaming: isCameraOn,
  error: cameraError,
  startCamera: initCamera,
  stopCamera: stopCameraFn,
  captureFrame,
} = useCamera();

const {
  isRecording: isMicRecording,
  isSpeaking: isMicSpeaking,
  error: micError,
  startMicrophone: initMic,
  stopMicrophone: stopMicFn,
} = useMicrophone();

const cameraLoading = ref(false);

async function toggleCamera() {
  if (isCameraOn.value) {
    stopCameraFn();
    // 停止 Qwen 图像流
    if (qwenImageInterval) {
      clearInterval(qwenImageInterval)
      qwenImageInterval = null
    }
  } else {
    cameraLoading.value = true;
    await initCamera();
    cameraLoading.value = false;
    // 启动 Qwen 图像流（如果是 Qwen 模式）
    updateQwenImageStream()
  }
}

function toggleMic() {
  if (isMicRecording.value) {
    stopMicFn();
  } else {
    initMic();
  }
}

/* ─── State Machine ─── */
const currentMode = ref("idle");
const statusText = ref("System Ready");
const showHint = ref(true);
const isLocalSending = ref(false);
const interimText = ref("");

/* ─── Text Input ─── */
const inputText = ref("");

/* ─── Quick Replies ─── */
const quickRepliesRef = ref(null);
let qrDragState = { isDown: false, startX: 0, scrollLeft: 0 };

function onQrMouseDown(e) {
  const el = quickRepliesRef.value;
  if (!el) return;
  qrDragState.isDown = true;
  qrDragState.startX = e.pageX - el.offsetLeft;
  qrDragState.scrollLeft = el.scrollLeft;
  el.style.cursor = "grabbing";
}
function onQrMouseMove(e) {
  if (!qrDragState.isDown) return;
  const el = quickRepliesRef.value;
  if (!el) return;
  e.preventDefault();
  const x = e.pageX - el.offsetLeft;
  el.scrollLeft = qrDragState.scrollLeft - (x - qrDragState.startX);
}
function onQrMouseUp() {
  qrDragState.isDown = false;
  const el = quickRepliesRef.value;
  if (el) el.style.cursor = "grab";
}

const quickReplies = [
  "帮我分析一下画面中的内容",
  "你好，请自我介绍一下",
  "今天天气怎么样？",
  "帮我写一段代码",
  "推荐一些学习方向",
  "解释一下量子计算",
  "给我说个笑话",
];

/* ─── Chat Messages ─── */
const chatScrollRef = ref(null);

/* ─── Canvas refs ─── */
const mainCanvasRef = ref(null);
const waveCanvasRef = ref(null);

/* ─── Voice Input (MediaRecorder + silence detection) ─── */
const speechSupported = ref(false);
let mediaRecorder = null;
let audioChunks = [];
let silenceTimer = null;
let audioCtx = null;
let analyser = null;
let recordingMimeType = "audio/webm";
let abortCtrl = null;

const SILENCE_THRESHOLD = 0.008;
const SILENCE_TIMEOUT_MS = 1400;

function initSpeech() {
  speechSupported.value = !!navigator.mediaDevices?.getUserMedia;
}

async function toggleVoice() {
  if (currentMode.value === "thinking" || currentMode.value === "speaking")
    return;
  if (!speechSupported.value) return;

  // 重新加载模型配置（可能在设置面板中被修改）
  const saved = localStorage.getItem('starvisionchat_config')
  if (saved) {
    try {
      const config = JSON.parse(saved)
      modelProvider.value = config.modelProvider || 'mimo'
    } catch { /* ignore */ }
  }

  if (currentMode.value !== "listening") {
    abortCtrl?.abort();
    setMode("listening");
    await startRecording();
  } else {
    stopRecording();
  }
}

async function startRecording() {
  audioChunks = [];
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioCtx = new AudioContext();
    const source = audioCtx.createMediaStreamSource(stream);
    analyser = audioCtx.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.3;
    source.connect(analyser);

    recordingMimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

    mediaRecorder = new MediaRecorder(stream, { mimeType: recordingMimeType });
    audioChunks = [];

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      if (audioCtx) {
        audioCtx.close();
        audioCtx = null;
      }
      if (silenceTimer) {
        clearTimeout(silenceTimer);
        silenceTimer = null;
      }
      analyser = null;

      if (audioChunks.length === 0) {
        setMode("idle");
        return;
      }
      const audioBlob = new Blob(audioChunks, { type: recordingMimeType });

      // 根据模型选择使用不同的发送方式
      if (modelProvider.value === 'qwen') {
        // Qwen 模式：流式发送音频
        await streamAudioToQwen(audioBlob);
      } else {
        // MiMo 模式：录音结束后一次性发送
        await sendVoiceAudio(audioBlob);
      }
    };

    mediaRecorder.onerror = () => {
      setMode("idle");
    };

    mediaRecorder.start(100);
    checkSilence();
  } catch {
    interimText.value = "麦克风权限被拒绝";
    setMode("idle");
  }
}

function checkSilence() {
  if (
    !analyser ||
    currentMode.value !== "listening" ||
    !mediaRecorder ||
    mediaRecorder.state !== "recording"
  )
    return;

  const data = new Uint8Array(analyser.fftSize);
  analyser.getByteTimeDomainData(data);
  let sumSq = 0;
  for (let i = 0; i < data.length; i++) {
    const n = (data[i] - 128) / 128;
    sumSq += n * n;
  }
  const rms = Math.sqrt(sumSq / data.length);

  if (rms < SILENCE_THRESHOLD) {
    if (!silenceTimer) {
      silenceTimer = setTimeout(() => stopRecording(), SILENCE_TIMEOUT_MS);
    }
  } else {
    if (silenceTimer) {
      clearTimeout(silenceTimer);
      silenceTimer = null;
    }
  }
  setTimeout(checkSilence, 100);
}

function stopRecording() {
  if (silenceTimer) {
    clearTimeout(silenceTimer);
    silenceTimer = null;
  }
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
}

/** WebM → WAV conversion */
async function convertToWav(audioBlob) {
  const ctx = new AudioContext();
  try {
    const buf = await ctx.decodeAudioData(await audioBlob.arrayBuffer());
    const ch = buf.getChannelData(0);
    const sr = buf.sampleRate;
    const nc = 1,
      bps = 16;
    const br = (sr * nc * bps) / 8,
      ba = (nc * bps) / 8;
    const dl = ch.length * ba;
    const ab = new ArrayBuffer(44 + dl);
    const v = new DataView(ab);
    writeStr(v, 0, "RIFF");
    v.setUint32(4, 36 + dl, true);
    writeStr(v, 8, "WAVE");
    writeStr(v, 12, "fmt ");
    v.setUint32(16, 16, true);
    v.setUint16(20, 1, true);
    v.setUint16(22, nc, true);
    v.setUint32(24, sr, true);
    v.setUint32(28, br, true);
    v.setUint16(32, ba, true);
    v.setUint16(34, bps, true);
    writeStr(v, 36, "data");
    v.setUint32(40, dl, true);
    let off = 44;
    for (let i = 0; i < ch.length; i++) {
      const s = Math.max(-1, Math.min(1, ch[i]));
      v.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      off += 2;
    }
    return new Blob([ab], { type: "audio/wav" });
  } finally {
    ctx.close();
  }
}

function writeStr(v, o, s) {
  for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i));
}

function arrayBufToB64(buf) {
  const bytes = new Uint8Array(buf);
  let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}

/** Send voice audio via WebSocket for STT */
async function sendVoiceAudio(audioBlob) {
  try {
    const wav = await convertToWav(audioBlob)
    const b64 = arrayBufToB64(await wav.arrayBuffer())

    // 捕获当前摄像头帧
    const frame = captureFrame()

    // Send audio via WebSocket（附带当前帧）
    setMode('thinking')
    wsService.sendAudioChunk(b64)
    wsService.sendAudioEnd(frame)
  } catch {
    setMode('idle')
  }
}

/** Stream audio in real-time for Qwen mode */
async function streamAudioToQwen(audioBlob) {
  try {
    // 转换为 16kHz PCM 格式（Qwen 要求）
    const pcm16k = await convertToPcm16k(audioBlob)
    const b64 = arrayBufToB64(pcm16k)

    // 流式发送音频到 Qwen
    wsService.send('audio_stream', { audio: b64 })

    // 捕获并发送当前摄像头帧
    const frame = captureFrame()
    if (frame) {
      wsService.send('image_stream', { image: frame })
    }
  } catch (e) {
    console.error('Qwen audio stream error:', e)
  }
}

/** 转换音频为 16kHz PCM16 格式（Qwen 要求） */
async function convertToPcm16k(audioBlob) {
  const ctx = new AudioContext({ sampleRate: 16000 })
  try {
    const buf = await ctx.decodeAudioData(await audioBlob.arrayBuffer())
    const ch = buf.getChannelData(0) // 单声道

    // PCM16 编码
    const pcm = new ArrayBuffer(ch.length * 2)
    const view = new DataView(pcm)
    for (let i = 0; i < ch.length; i++) {
      const s = Math.max(-1, Math.min(1, ch[i]))
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    }
    return pcm
  } finally {
    ctx.close()
  }
}

/* ─── Session Management ─── */
function createNewSession() {
  sessionStore.createSession()
  chatStore.loadSession([])
  showSessionList.value = false
}

function switchToSession(id) {
  const messages = sessionStore.switchSession(id)
  chatStore.loadSession(messages)
  showSessionList.value = false
}

function deleteSession(id) {
  sessionStore.deleteSession(id)
  // 如果删除后当前会话变了，加载新当前会话的消息
  if (sessionStore.currentSessionId !== id) {
    chatStore.loadSession(sessionStore.currentMessages)
  }
}

function formatSessionTime(date) {
  if (!date) return ''
  const d = date instanceof Date ? date : new Date(date)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

/* ─── AI Response Handling ─── */
let typewriterTimer = null;
let currentAudio = null;

function handleAIResponse(data) {
  const text = data.text || "";
  const isUser = data.is_user || false;

  if (isUser) {
    // Voice input transcribed text — add as user message
    if (text) {
      chatStore.addMessage(text, true);
      scrollChat();
    }
    return;
  }

  // AI response - display with typewriter effect
  if (text) {
    typewriterEffect(text);
  }
}

/** Play MiMo TTS audio from backend */
function handleAIAudio(data) {
  const audioBase64 = data.audio;
  if (!audioBase64) return;

  try {
    // Stop any currently playing audio
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }

    // Decode base64 WAV and create blob
    const binaryStr = atob(audioBase64);
    const bytes = new Uint8Array(binaryStr.length);
    for (let i = 0; i < binaryStr.length; i++) {
      bytes[i] = binaryStr.charCodeAt(i);
    }
    const blob = new Blob([bytes], { type: "audio/wav" });
    const url = URL.createObjectURL(blob);

    const audio = new Audio(url);
    currentAudio = audio;

    audio.onplay = () => {
      setMode("speaking");
    };

    audio.onended = () => {
      URL.revokeObjectURL(url);
      currentAudio = null;
      setMode("idle");
    };

    audio.onerror = () => {
      URL.revokeObjectURL(url);
      currentAudio = null;
      setMode("idle");
    };

    audio.play();
  } catch (e) {
    console.error("Failed to play AI audio:", e);
  }
}

/* ─── Qwen Realtime Handlers ─── */
let qwenAudioContext = null;
let qwenAudioQueue = [];
let qwenIsPlaying = false;

function handleQwenTextDelta(data) {
  // 流式追加文本到当前 AI 回复
  const text = data.text || "";
  if (!text) return;

  // 找到最后一条 AI 消息并追加
  const messages = chatStore.messages;
  const lastMsg = messages[messages.length - 1];
  if (lastMsg && !lastMsg.isUser) {
    lastMsg.text += text;
  } else {
    chatStore.addMessage(text, false);
  }
}

function handleQwenAudioDelta(data) {
  // 接收 Qwen 音频流（base64 PCM16 24kHz）
  const audioBase64 = data.audio;
  if (!audioBase64) return;

  try {
    const binaryStr = atob(audioBase64);
    const bytes = new Uint8Array(binaryStr.length);
    for (let i = 0; i < binaryStr.length; i++) {
      bytes[i] = binaryStr.charCodeAt(i);
    }

    // PCM16 24kHz → float32
    const float32 = new Float32Array(bytes.length / 2);
    for (let i = 0; i < float32.length; i++) {
      const int16 = (bytes[i * 2 + 1] << 8) | bytes[i * 2];
      float32[i] = (int16 < 32768 ? int16 : int16 - 65536) / 32768;
    }

    qwenAudioQueue.push(float32);
    if (!qwenIsPlaying) {
      playQwenAudioQueue();
    }
  } catch (e) {
    console.error("Qwen audio decode error:", e);
  }
}

function playQwenAudioQueue() {
  if (qwenAudioQueue.length === 0) {
    qwenIsPlaying = false;
    setMode("idle");
    return;
  }

  qwenIsPlaying = true;
  setMode("speaking");

  if (!qwenAudioContext) {
    qwenAudioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
  }

  const float32 = qwenAudioQueue.shift();
  const buffer = qwenAudioContext.createBuffer(1, float32.length, 24000);
  buffer.getChannelData(0).set(float32);

  const source = qwenAudioContext.createBufferSource();
  source.buffer = buffer;
  source.connect(qwenAudioContext.destination);
  source.onended = () => playQwenAudioQueue();
  source.start();
}

function handleQwenTranscript(data) {
  // 用户语音转录完成
  const text = data.text || "";
  if (text) {
    chatStore.addMessage(text, true);
    scrollChat();
  }
}

function handleQwenResponseDone() {
  // Qwen 响应完成
  qwenIsPlaying = false;
  setMode("idle");
}

function typewriterEffect(text) {
  if (typewriterTimer) clearInterval(typewriterTimer);

  // Add empty assistant message
  chatStore.addMessage("", false);
  const msgIndex = chatStore.messages.length - 1;
  let charIndex = 0;

  typewriterTimer = setInterval(() => {
    if (charIndex < text.length) {
      chatStore.messages[msgIndex].text += text[charIndex];
      feedStreamChunk(text[charIndex]);
      charIndex++;
      scrollChat();
    } else {
      clearInterval(typewriterTimer);
      typewriterTimer = null;
      flushStreamBuffer();
      setMode("speaking");
      setTimeout(() => setMode("idle"), 1500);
      isLocalSending.value = false;
    }
  }, 20);
}

/* ─── Status handling ─── */
function handleStatus(data) {
  const status = data.status || "idle";
  if (status === "thinking") {
    setMode("thinking");
  } else if (status === "speaking") {
    setMode("speaking");
  } else if (status === "processing_stt") {
    setMode("thinking");
    interimText.value = "正在识别语音...";
  } else if (status === "processing_vision") {
    // vision processing
  } else if (status === "idle") {
    if (!isLocalSending.value) {
      setMode("idle");
    }
  }
}

/* ─── Mode Management ─── */
function setMode(mode) {
  currentMode.value = mode;
  showHint.value = mode === "idle";
  if (mode === "idle") {
    statusText.value = "System Ready";
  } else if (mode === "listening") {
    statusText.value = "Listening...";
  } else if (mode === "thinking") {
    statusText.value = "Processing";
    interimText.value = "";
  } else if (mode === "speaking") {
    statusText.value = "Transmitting";
  }
}

/* ─── Send Text ─── */
function handleTextSend() {
  const text = inputText.value.trim();
  if (!text || isLocalSending.value) return;

  chatStore.addMessage(text, true);

  // 捕获当前摄像头帧，和消息一起发送
  const frame = captureFrame()
  wsService.sendTextInput(text, frame)

  inputText.value = "";
  isLocalSending.value = true;
  setMode("thinking");
}

function onInputKeydown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleTextSend();
  }
}

function useQuickReply(text) {
  if (isLocalSending.value) return;
  inputText.value = text;
}

function scrollChat() {
  nextTick(() => {
    if (chatScrollRef.value) {
      chatScrollRef.value.scrollTo({
        top: chatScrollRef.value.scrollHeight,
        behavior: "auto",
      });
    }
  });
}

/* ─── Markdown ─── */
marked.use({ breaks: false, gfm: true });
const renderer = new marked.Renderer();
renderer.code = ({ text, lang }) => {
  const la = lang ? ` class="language-${lang}"` : "";
  try {
    const h = lang
      ? hljs.highlight(text, { language: lang }).value
      : hljs.highlightAuto(text).value;
    return `<pre><code${la}>${h}</code></pre>`;
  } catch {
    return `<pre><code${la}>${hljs.highlightAuto(text).value}</code></pre>`;
  }
};
marked.use({ renderer });

function fmt(s) {
  if (!s) return "";
  try {
    let cleaned = s
      .trim()
      .replace(/^\n+/, "")
      .replace(/\n+$/, "")
      .replace(/\n{2,}/g, "\n");
    return marked
      .parse(cleaned)
      .replace(/<table>/g, '<table class="chat-table">')
      .replace(/<p>\s*<\/p>/g, "")
      .trim();
  } catch {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\n/g, "<br>");
  }
}

/* ═══════════════════════════════════════════
   3D Particle Sphere + Background Stars
   ═══════════════════════════════════════════ */
const SPHERE_RADIUS = 180;
const PARTICLE_COUNT = 800;
const BG_STAR_COUNT = 250;

let animId = 0;
let width = 0;
let height = 0;
let rotX = 0;
let rotY = 0;
let isDragging = false;
let lastMX = 0;
let lastMY = 0;
let targetSpeed = 1;
let curSpeed = 1;
let audioLevel = 0;

/* Theme-aware colors */
function getThemeColor(varName, fallback) {
  const val = getComputedStyle(document.documentElement)
    .getPropertyValue(varName)
    .trim();
  return val || fallback;
}

function isDarkTheme() {
  const canvas = getThemeColor("--canvas", "#FFFCF7");
  const hex = canvas.replace("#", "");
  if (hex.length >= 6) {
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    return (r * 299 + g * 587 + b * 114) / 1000 < 128;
  }
  return true;
}

function getParticleColors() {
  const dark = isDarkTheme();
  const accent = getThemeColor("--accent", "#E85D2A");
  const warm = getThemeColor("--warm", "#E8A860");
  return {
    signal: accent,
    core: warm,
    void: dark ? "rgba(255,255,255,0.15)" : `${warm}33`,
    star: dark ? "rgba(255,255,255,0.5)" : `${accent}88`,
    idle: accent,
    listening: accent,
    thinking: warm,
    speaking: dark ? "rgba(255,255,255,0.8)" : accent,
  };
}

let themeColors = getParticleColors();

const modeColorMap = reactive({
  idle: themeColors.idle,
  listening: themeColors.listening,
  thinking: themeColors.thinking,
  speaking: themeColors.speaking,
});

const themeObserver = new MutationObserver(() => {
  themeColors = getParticleColors();
  modeColorMap.idle = themeColors.idle;
  modeColorMap.listening = themeColors.listening;
  modeColorMap.thinking = themeColors.thinking;
  modeColorMap.speaking = themeColors.speaking;
});

let bgStars = [];

class OrbP {
  constructor() {
    const u = Math.random(),
      v = Math.random();
    const r = Math.pow(Math.random(), 1 / 3) * SPHERE_RADIUS;
    const th = 2 * Math.PI * u,
      ph = Math.acos(2 * v - 1);
    this.bx = r * Math.sin(ph) * Math.cos(th);
    this.by = r * Math.sin(ph) * Math.sin(th);
    this.bz = r * Math.cos(ph);
    const rnd = Math.random();
    if (rnd < 0.4) {
      this.type = "signal";
      this.color = themeColors.signal;
    } else if (rnd < 0.8) {
      this.type = "core";
      this.color = themeColors.core;
    } else {
      this.type = "void";
      this.color = themeColors.void;
    }
    this.size = Math.random() * 1.5 + 0.5;
    this.x = 0;
    this.y = 0;
    this.z = 0;
  }

  update(time, rx, ry, mode) {
    if (this.type === "signal") this.color = modeColorMap[mode] || "#ff4d4d";
    const wave =
      Math.sin(time * 0.002 + (this.bx + this.by + this.bz) * 0.01) *
      (15 + audioLevel * 50);
    const ru = Math.sqrt(this.bx ** 2 + this.by ** 2 + this.bz ** 2) + 0.001;
    const sc = mode === "thinking" ? 0.9 : 1;
    const rf = (ru * sc + wave) / ru;
    let tx = this.bx * rf,
      ty = this.by * rf,
      tz = this.bz * rf;
    const cx = Math.cos(rx),
      sx = Math.sin(rx);
    const cy = Math.cos(ry),
      sy = Math.sin(ry);
    const y1 = ty * cx - tz * sx,
      z1 = ty * sx + tz * cx;
    this.x = tx * cy + z1 * sy;
    this.y = y1;
    this.z = -tx * sy + z1 * cy;
  }

  draw(ctx, cx, cy) {
    const p = 600 / (600 - Math.max(-300, Math.min(this.z, 590)));
    const dx = this.x * p + cx,
      dy = this.y * p + cy,
      ds = Math.max(0, this.size * p);
    if (this.type === "void") {
      ctx.strokeStyle = this.color;
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.arc(dx, dy, ds, 0, Math.PI * 2);
      ctx.stroke();
    } else {
      ctx.fillStyle = this.color;
      ctx.globalAlpha = Math.max(0.1, p - 0.4);
      ctx.beginPath();
      ctx.arc(dx, dy, ds, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

let orbParticles = [];

/* ═══════════════════════════════════════════
   Wave Animation
   ═══════════════════════════════════════════ */
const waveLayers = [
  { speed: 0.005, freq: 0.006, alpha: 0.8, offset: 0, scale: 1.0 },
  { speed: 0.0075, freq: 0.008, alpha: 0.5, offset: 2, scale: 0.8 },
  { speed: 0.004, freq: 0.005, alpha: 0.3, offset: 4, scale: 0.6 },
  { speed: 0.01, freq: 0.01, alpha: 0.2, offset: 6, scale: 0.4 },
];

let targetWaveW = 160,
  curWaveW = 160;
let targetAmp = 0,
  curAmp = 0;
let targetMorph = 1,
  curMorph = 1;

function renderWave(time) {
  const c = waveCanvasRef.value;
  if (!c) return;
  const ctx = c.getContext("2d");
  if (!ctx) return;
  const w = c.width,
    h = c.height,
    cy = h / 2,
    cx = w / 2;
  ctx.clearRect(0, 0, w, h);

  const mode = currentMode.value;
  if (mode === "idle") {
    targetWaveW = 160;
    targetMorph = 1;
    targetAmp = 0;
  } else if (mode === "listening") {
    targetWaveW = w * 0.7;
    targetMorph = 0;
    targetAmp = 0.3 + Math.sin(time * 0.005) * 0.1;
  } else if (mode === "thinking") {
    targetWaveW = w * 0.5;
    targetMorph = 0;
    targetAmp = 0.2 + Math.random() * 0.1;
  } else if (mode === "speaking") {
    targetWaveW = w * 0.9;
    targetMorph = 0;
    targetAmp = 0.2 + audioLevel * 0.8;
  }

  curMorph += (targetMorph - curMorph) * 0.08;
  curWaveW += (targetWaveW - curWaveW) * 0.1;
  curAmp += (targetAmp - curAmp) * 0.1;
  const waveAlpha = 1 - curMorph;

  // Liquid orb (idle state)
  if (curMorph > 0.005) {
    ctx.save();
    ctx.translate(cx, cy);
    ctx.scale(1 + (1 - curMorph) * 6, 1 - (1 - curMorph) * 0.8);
    ctx.globalAlpha = curMorph;
    const orbSize = 55 + Math.sin(time * 0.003) * 4;
    ctx.globalCompositeOperation = "screen";
    ctx.rotate(time * 0.001);
    const colors = [
      { r: 255, g: 128, b: 181, radius: orbSize * 1.3, offset: 0, dist: 12 },
      { r: 129, g: 230, b: 217, radius: orbSize * 1.2, offset: 2.1, dist: 18 },
      { r: 167, g: 139, b: 250, radius: orbSize * 1.4, offset: 4.2, dist: 10 },
    ];
    colors.forEach((item, idx) => {
      ctx.save();
      ctx.rotate(time * 0.002 * (idx % 2 === 0 ? 1 : -1) + item.offset);
      ctx.translate(item.dist, 0);
      const g = ctx.createRadialGradient(0, 0, 0, 0, 0, item.radius);
      g.addColorStop(0, `rgba(${item.r},${item.g},${item.b},0.9)`);
      g.addColorStop(0.5, `rgba(${item.r},${item.g},${item.b},0.4)`);
      g.addColorStop(1, `rgba(${item.r},${item.g},${item.b},0)`);
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(0, 0, item.radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    });
    ctx.globalCompositeOperation = "source-over";
    const cg = ctx.createRadialGradient(0, 0, 0, 0, 0, orbSize * 0.7);
    cg.addColorStop(0, "rgba(255,255,255,1)");
    cg.addColorStop(0.3, "rgba(255,255,255,0.7)");
    cg.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = cg;
    ctx.beginPath();
    ctx.arc(0, 0, orbSize * 0.7, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }

  // Sound waves
  if (waveAlpha > 0.005) {
    ctx.save();
    ctx.globalAlpha = waveAlpha;
    ctx.globalCompositeOperation = "screen";
    const grad = ctx.createLinearGradient(0, 0, w, 0);
    grad.addColorStop(0.1, "#ff80b5");
    grad.addColorStop(0.5, "#a78bfa");
    grad.addColorStop(0.9, "#81e6d9");
    const sx = cx - curWaveW / 2,
      ex = cx + curWaveW / 2;
    waveLayers.forEach((layer) => {
      ctx.beginPath();
      ctx.moveTo(sx, cy);
      for (let x = sx; x <= ex; x += 2) {
        const prog = (x - sx) / curWaveW;
        const env = Math.pow(Math.sin(prog * Math.PI), 2.5);
        const yOff =
          Math.sin(x * layer.freq + time * layer.speed + layer.offset) *
          ((h / 2) * curAmp * layer.scale * env);
        ctx.lineTo(x, cy + yOff);
      }
      for (let x = ex; x >= sx; x -= 2) {
        const prog = (x - sx) / curWaveW;
        const env = Math.pow(Math.sin(prog * Math.PI), 2.5);
        const yOff =
          Math.sin(
            x * layer.freq + time * layer.speed + layer.offset + Math.PI,
          ) *
          ((h / 2) * curAmp * layer.scale * env);
        ctx.lineTo(x, cy + yOff);
      }
      ctx.closePath();
      ctx.fillStyle = grad;
      ctx.globalAlpha = layer.alpha * waveAlpha * 1.2;
      ctx.fill();
    });
    ctx.restore();
  }
}

/* ═══════════════════════════════════════════
   Main Animation Loop
   ═══════════════════════════════════════════ */
function resizeMain() {
  const c = mainCanvasRef.value;
  if (!c) return;
  width = window.innerWidth;
  height = window.innerHeight;
  c.width = width;
  c.height = height;
  bgStars = Array.from({ length: BG_STAR_COUNT }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    size: Math.random() * 1.5 + 0.2,
    speed: Math.random() * 0.3 + 0.05,
    twinkle: Math.random() * 0.003 + 0.001,
    phase: Math.random() * Math.PI * 2,
  }));
}

function resizeWave() {
  const c = waveCanvasRef.value;
  if (!c) return;
  const p = c.parentElement;
  if (!p) return;
  c.width = p.clientWidth * 2;
  c.height = p.clientHeight * 2;
}

function animate(time) {
  const c = mainCanvasRef.value;
  if (!c) return;
  const ctx = c.getContext("2d");
  if (!ctx) return;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = themeColors.star;

  bgStars.forEach((s) => {
    s.y -= s.speed;
    if (s.y < 0) s.y = height;
    ctx.globalAlpha = Math.max(
      0.05,
      0.4 + Math.sin(time * s.twinkle + s.phase) * 0.4,
    );
    ctx.beginPath();
    ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
    ctx.fill();
  });
  ctx.globalAlpha = 1;

  curSpeed += (targetSpeed - curSpeed) * 0.05;

  if (currentMode.value === "speaking") {
    audioLevel +=
      (Math.max(
        0,
        Math.sin(time * 0.015) * Math.sin(time * 0.005) * Math.random(),
      ) *
        1.5 -
        audioLevel) *
      0.2;
  } else {
    audioLevel += (0 - audioLevel) * 0.1;
  }

  if (!isDragging) {
    rotY += 0.005 * curSpeed;
    rotX += 0.002 * curSpeed;
  }

  for (const p of orbParticles) p.update(time, rotX, rotY, currentMode.value);
  orbParticles.sort((a, b) => a.z - b.z);
  for (const p of orbParticles) p.draw(ctx, width / 2, height / 2);

  renderWave(time);
  animId = requestAnimationFrame(animate);
}

/* Mouse drag for sphere rotation */
function onDown(e) {
  isDragging = true;
  const cx = "clientX" in e ? e.clientX : e.touches[0].clientX;
  const cy = "clientY" in e ? e.clientY : e.touches[0].clientY;
  lastMX = cx;
  lastMY = cy;
}
function onMove(e) {
  if (!isDragging) return;
  const cx = "clientX" in e ? e.clientX : e.touches[0].clientX;
  const cy = "clientY" in e ? e.clientY : e.touches[0].clientY;
  rotY += (cx - lastMX) * 0.01;
  rotX -= (cy - lastMY) * 0.01;
  lastMX = cx;
  lastMY = cy;
}
function onUp() {
  isDragging = false;
}

/* ─── Lifecycle ─── */
onMounted(() => {
  // 加载当前会话的消息
  chatStore.loadSession(sessionStore.currentMessages)

  orbParticles = Array.from({ length: PARTICLE_COUNT }, () => new OrbP());
  resizeMain();
  resizeWave();
  window.addEventListener("resize", resizeMain);
  window.addEventListener("resize", resizeWave);
  animId = requestAnimationFrame(animate);
  initSpeech();

  // 自动开启摄像头（让用户可以立即与 AI 视觉交互）
  setTimeout(async () => {
    await initCamera()
    // 启动 Qwen 图像流（如果是 Qwen 模式）
    updateQwenImageStream()
  }, 500)

  // Listen for theme changes
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });

  // Register WebSocket listeners
  wsService.on("ai_response", handleAIResponse);
  wsService.on("ai_audio", handleAIAudio);
  wsService.on("status", handleStatus);

  // Qwen realtime listeners
  wsService.on("qwen_text_delta", handleQwenTextDelta);
  wsService.on("qwen_audio_delta", handleQwenAudioDelta);
  wsService.on("qwen_transcript", handleQwenTranscript);
  wsService.on("qwen_response_done", handleQwenResponseDone);
});

onBeforeUnmount(() => {
  cancelAnimationFrame(animId);
  window.removeEventListener("resize", resizeMain);
  window.removeEventListener("resize", resizeWave);
  themeObserver.disconnect();
  if (silenceTimer) clearTimeout(silenceTimer);
  if (typewriterTimer) clearInterval(typewriterTimer);
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
  }
  mediaRecorder?.stop();
  audioCtx?.close();
  abortCtrl?.abort();
  resetTTS();

  // Remove WebSocket listeners
  wsService.off("ai_response", handleAIResponse);
  wsService.off("status", handleStatus);

  // Qwen listeners cleanup
  wsService.off("qwen_text_delta", handleQwenTextDelta);
  wsService.off("qwen_audio_delta", handleQwenAudioDelta);
  wsService.off("qwen_transcript", handleQwenTranscript);
  wsService.off("qwen_response_done", handleQwenResponseDone);

  // Qwen audio cleanup
  if (qwenAudioContext) {
    qwenAudioContext.close();
    qwenAudioContext = null;
  }

  // Qwen image stream cleanup
  if (qwenImageInterval) {
    clearInterval(qwenImageInterval)
    qwenImageInterval = null
  }
});

watch(
  () => chatStore.messages.length,
  () => scrollChat(),
);
</script>

<template>
  <div class="immersive-overlay">
    <!-- Glow background -->
    <div
      class="glow-bg"
      :style="{ backgroundColor: modeColorMap[currentMode] || '#ef4444' }"
    ></div>

    <!-- Main particle canvas -->
    <canvas
      ref="mainCanvasRef"
      class="main-canvas"
      @mousedown="onDown"
      @mousemove="onMove"
      @mouseup="onUp"
      @mouseleave="onUp"
      @touchstart.prevent="onDown"
      @touchmove.prevent="onMove"
      @touchend="onUp"
    ></canvas>

    <!-- Top bar: brand + theme dots + settings -->
    <div class="top-bar">
      <div class="top-brand">
        <el-icon :size="18" color="var(--accent)"><Star /></el-icon>
        <span class="top-brand-name">StarVision</span>
        <span class="model-badge" :class="modelProvider">
          {{ modelProvider === 'qwen' ? 'Qwen' : 'MiMo' }}
        </span>
      </div>
      <div class="top-actions">
        <!-- Theme dots -->
        <div class="theme-dots">
          <span
            v-for="t in themes"
            :key="t.id"
            class="theme-dot"
            :class="{ active: currentTheme === t.id }"
            :style="{ backgroundColor: t.color }"
            :title="t.name"
            @click="setTheme(t.id)"
          ></span>
        </div>
        <!-- Settings -->
        <SettingsPanel />
      </div>
    </div>

    <!-- Video stream overlay (bottom-left) -->
    <div class="video-mini-overlay">
      <div class="video-mini-wrapper">
        <video
          ref="videoRef"
          autoplay
          muted
          playsinline
          class="video-mini-element"
        />
        <div v-if="!isCameraOn" class="video-mini-placeholder">
          <el-icon :size="24"><VideoCamera /></el-icon>
        </div>
        <!-- Speaking indicator -->
        <div v-if="isMicSpeaking" class="video-mini-speaking">
          <div class="pulse-ring"></div>
        </div>
      </div>
      <div class="video-mini-controls">
        <button
          class="mini-ctrl-btn"
          @click="toggleCamera"
          :title="isCameraOn ? '关闭摄像头' : '开启摄像头'"
        >
          <el-icon v-if="cameraLoading"><Loading /></el-icon>
          <el-icon v-else-if="isCameraOn"><VideoPause /></el-icon>
          <el-icon v-else><VideoCamera /></el-icon>
        </button>
        <button
          class="mini-ctrl-btn"
          :class="{ active: isMicRecording }"
          @click="toggleMic"
          :title="isMicRecording ? '关闭麦克风' : '开启麦克风'"
          :disabled="!isCameraOn"
        >
          <el-icon v-if="isMicRecording"><Mute /></el-icon>
          <el-icon v-else><Microphone /></el-icon>
        </button>
      </div>
    </div>

    <!-- Mic wave area (center-bottom) -->
    <div class="mic-wrapper">
      <div
        class="wave-container"
        @click="toggleVoice"
        title="点击开始/结束说话"
      >
        <canvas ref="waveCanvasRef" class="wave-canvas"></canvas>
        <div class="interaction-hint" :class="{ hidden: !showHint }">
          [ 点击以语音交流 ]
        </div>
      </div>
      <div class="status-text" :class="currentMode">{{ statusText }}</div>
      <div v-if="interimText" class="interim-text">{{ interimText }}</div>
    </div>

    <!-- Session list sidebar -->
    <Transition name="session-slide">
      <div v-if="showSessionList" class="session-sidebar" @click.self="showSessionList = false">
        <div class="session-sidebar-inner">
          <div class="session-sidebar-header">
            <span>会话列表</span>
            <button class="session-close-btn" @click="showSessionList = false">
              <el-icon><Close /></el-icon>
            </button>
          </div>
          <div class="session-list">
            <div
              v-for="session in sessionStore.sessions"
              :key="session.id"
              class="session-item"
              :class="{ active: session.id === sessionStore.currentSessionId }"
              @click="switchToSession(session.id)"
            >
              <div class="session-item-content">
                <div class="session-title">{{ session.title }}</div>
                <div class="session-time">{{ formatSessionTime(session.updatedAt) }}</div>
              </div>
              <button
                class="session-delete-btn"
                @click.stop="deleteSession(session.id)"
                title="删除会话"
              >
                <el-icon><Delete /></el-icon>
              </button>
            </div>
            <div v-if="sessionStore.sessions.length === 0" class="session-empty">
              暂无会话
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Chat panel (right side) -->
    <div class="chat-panel">
      <div class="chat-header">
        <button
          class="session-menu-btn"
          @click="showSessionList = !showSessionList"
          title="会话列表"
        >
          <el-icon><ChatDotRound /></el-icon>
          <span class="session-count">{{ sessionStore.sessions.length }}</span>
        </button>
        <span>STARVISION CHAT</span>
        <div class="chat-header-actions">
          <button
            class="chat-new-btn"
            @click="createNewSession()"
            title="新建会话"
          >
            <el-icon><Plus /></el-icon>
          </button>
          <button
            v-if="chatStore.messages.length > 0"
            class="chat-clear-btn"
            @click="chatStore.clearMessages()"
            title="清空对话"
          >
            清空
          </button>
        </div>
      </div>

      <div ref="chatScrollRef" class="chat-messages">
        <!-- Empty state -->
        <div v-if="chatStore.messages.length === 0" class="chat-empty">
          <p>开启摄像头和麦克风</p>
          <p>或在下方输入文字开始对话</p>
        </div>

        <div
          v-for="(msg, i) in chatStore.messages"
          :key="msg.id || i"
          class="msg"
          :class="msg.isUser ? 'user' : 'assistant'"
        >
          <div class="msg-avatar">
            <el-icon v-if="msg.isUser"><User /></el-icon>
            <el-icon v-else><Star /></el-icon>
          </div>
          <div class="msg-body">
            <div class="text" v-html="fmt(msg.text)"></div>
          </div>
        </div>

        <!-- Loading indicator -->
        <div
          v-if="
            isLocalSending &&
            !chatStore.isStreaming &&
            currentMode === 'thinking'
          "
          class="msg assistant"
        >
          <div class="msg-avatar">
            <el-icon><Star /></el-icon>
          </div>
          <div class="msg-body">
            <div class="imm-typing">
              <span class="dot"></span>
              <span class="dot"></span>
              <span class="dot"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick replies -->
      <div
        ref="quickRepliesRef"
        class="imm-quick-replies"
        @mousedown="onQrMouseDown"
        @mousemove="onQrMouseMove"
        @mouseup="onQrMouseUp"
        @mouseleave="onQrMouseUp"
      >
        <button
          v-for="item in quickReplies"
          :key="item"
          type="button"
          class="imm-qr-btn"
          :disabled="isLocalSending"
          @click="useQuickReply(item)"
        >
          {{ item }}
        </button>
      </div>

      <!-- Input area -->
      <div class="imm-input-area">
        <textarea
          v-model="inputText"
          class="imm-textarea"
          rows="2"
          placeholder="输入消息，或点击左侧语音..."
          :disabled="isLocalSending"
          @keydown="onInputKeydown"
        ></textarea>
        <div class="imm-input-actions">
          <div class="imm-input-tip">
            {{
              !chatStore.isConnected
                ? "未连接"
                : isLocalSending
                  ? "回复中..."
                  : "Enter 发送"
            }}
          </div>
          <button
            type="button"
            class="imm-send-btn"
            :disabled="
              isLocalSending || !inputText.trim() || !chatStore.isConnected
            "
            @click="handleTextSend"
          >
            <el-icon><Promotion /></el-icon>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.immersive-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background-color: var(--canvas);
  background-image:
    radial-gradient(circle at 15% 25%, var(--orb-1) 0%, transparent 40%),
    radial-gradient(circle at 85% 75%, var(--orb-2) 0%, transparent 40%);
  font-family: "LXGW WenKai", "Noto Sans SC", system-ui, sans-serif;
  color: var(--ink);
  overflow: hidden;
}

.glow-bg {
  position: absolute;
  width: 500px;
  height: 500px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.3;
  pointer-events: none;
  transition: background-color 0.8s ease;
  z-index: 5;
}

.main-canvas {
  display: block;
  position: absolute;
  inset: 0;
  z-index: 10;
  cursor: grab;
}
.main-canvas:active {
  cursor: grabbing;
}

/* ─── Top Bar ─── */
.top-bar {
  position: absolute;
  top: 16px;
  left: 24px;
  right: 24px;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: space-between;
  pointer-events: none;
}
.top-bar > * {
  pointer-events: auto;
}

.top-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.top-brand-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.5px;
}

.model-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.model-badge.mimo {
  background: var(--accent-soft);
  color: var(--accent);
}

.model-badge.qwen {
  background: rgba(59, 125, 216, 0.15);
  color: #3B7DD8;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tts-toggle-btn {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--ink-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  backdrop-filter: blur(8px);
}
.tts-toggle-btn:hover {
  background: var(--surface-hover);
  color: var(--ink);
  border-color: var(--border-interactive);
}
.tts-toggle-btn.active {
  background: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent);
  box-shadow: 0 0 12px rgba(139, 92, 246, 0.2);
}

.theme-dots {
  display: flex;
  gap: 6px;
  align-items: center;
}

.theme-dot {
  display: inline-block;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
}
.theme-dot:hover {
  transform: scale(1.2);
}
.theme-dot.active {
  border-color: var(--ink);
  box-shadow: 0 0 0 2px var(--canvas);
}

/* ─── Video mini overlay (bottom-left) ─── */
.video-mini-overlay {
  position: absolute;
  bottom: 40px;
  left: 24px;
  z-index: 30;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}

.video-mini-wrapper {
  width: 180px;
  height: 135px;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid var(--border);
  background: var(--canvas-deep);
  position: relative;
  box-shadow: var(--shadow-card);
}

.video-mini-element {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-mini-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-muted);
}

.video-mini-speaking {
  position: absolute;
  bottom: 8px;
  right: 8px;
}

.pulse-ring {
  width: 12px;
  height: 12px;
  background: #4caf50;
  border-radius: 50%;
  animation: pulse 1.5s infinite;
}

.video-mini-controls {
  display: flex;
  gap: 6px;
}

.mini-ctrl-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--ink-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  backdrop-filter: blur(8px);
  font-size: 14px;
}
.mini-ctrl-btn:hover {
  background: var(--surface-hover);
  color: var(--ink);
  border-color: var(--border-interactive);
}
.mini-ctrl-btn.active {
  background: rgba(76, 175, 80, 0.15);
  border-color: #4caf50;
  color: #4caf50;
}
.mini-ctrl-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ─── Mic wave area (center-bottom) ─── */
.mic-wrapper {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 30;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.wave-container {
  width: 360px;
  height: 160px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  position: relative;
}

.wave-canvas {
  display: block;
  width: 100%;
  height: 100%;
  pointer-events: none;
  transition: opacity 0.3s;
}
.wave-container:hover .wave-canvas {
  filter: brightness(1.3);
}

.interaction-hint {
  position: absolute;
  bottom: 10px;
  font-size: 12px;
  letter-spacing: 2px;
  color: var(--ink-muted);
  pointer-events: none;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  animation: breathe-text 2s infinite ease-in-out;
  opacity: 1;
  transform: translateY(0);
}
.interaction-hint.hidden {
  opacity: 0;
  transform: translateY(15px);
  animation: none;
}
@keyframes breathe-text {
  0%,
  100% {
    opacity: 0.4;
  }
  50% {
    opacity: 0.9;
    text-shadow: 0 0 10px rgba(255, 255, 255, 0.4);
  }
}

.status-text {
  font-size: 11px;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: var(--ink-muted);
  font-weight: bold;
  transition: color 0.3s;
}
.status-text.listening {
  color: var(--accent);
}
.status-text.thinking {
  color: var(--warm);
}
.status-text.speaking {
  color: var(--accent);
}

.interim-text {
  font-size: 13px;
  color: var(--ink-soft);
  max-width: 300px;
  text-align: center;
  animation: fadeInUp 0.3s ease;
}
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ─── Chat Panel (right side) ─── */
.chat-panel {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 420px;
  padding: 40px 24px 32px 24px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  z-index: 20;
  pointer-events: none;
  background: linear-gradient(
    to right,
    transparent 0%,
    var(--canvas) 60%,
    var(--canvas) 100%
  );
  -webkit-mask-image: linear-gradient(
    to bottom,
    transparent 0%,
    black 6%,
    black 92%,
    transparent 100%
  );
  mask-image: linear-gradient(
    to bottom,
    transparent 0%,
    black 6%,
    black 92%,
    transparent 100%
  );
}

.chat-header {
  padding-top: 30px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 3px;
  color: var(--ink-muted);
  margin-bottom: 20px;
  text-align: right;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  justify-content: space-between;
  pointer-events: auto;
}

.chat-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.session-menu-btn {
  position: relative;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--ink-muted);
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 4px 10px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}
.session-menu-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-soft);
}
.session-count {
  font-size: 10px;
  font-weight: 700;
  background: var(--accent);
  color: #fff;
  border-radius: 50%;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-new-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--ink-muted);
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}
.chat-new-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-soft);
}

/* ─── Session Sidebar ─── */
.session-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
  display: flex;
  justify-content: flex-end;
  pointer-events: auto;
  background: rgba(0,0,0,0.2);
  backdrop-filter: blur(2px);
}

.session-sidebar-inner {
  width: 300px;
  height: 100%;
  background: var(--surface);
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 20px rgba(0,0,0,0.1);
}

.session-slide-enter-active,
.session-slide-leave-active {
  transition: opacity 0.3s ease;
}
.session-slide-enter-active .session-sidebar-inner,
.session-slide-leave-active .session-sidebar-inner {
  transition: transform 0.3s ease;
}
.session-slide-enter-from,
.session-slide-leave-to {
  opacity: 0;
}
.session-slide-enter-from .session-sidebar-inner,
.session-slide-leave-to .session-sidebar-inner {
  transform: translateX(100%);
}

.session-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 50px 16px 16px;
  font-size: 13px;
  font-weight: 700;
  color: var(--ink);
  border-bottom: 1px solid var(--border);
}

.session-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--ink-muted);
  cursor: pointer;
  transition: all 0.2s;
}
.session-close-btn:hover {
  background: var(--accent-soft);
  color: var(--accent);
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 4px;
}
.session-item:hover {
  background: var(--surface-hover);
}
.session-item.active {
  background: var(--accent-soft);
  border: 1px solid var(--accent);
}

.session-item-content {
  flex: 1;
  min-width: 0;
}

.session-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-time {
  font-size: 11px;
  color: var(--ink-muted);
  margin-top: 2px;
}

.session-delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--ink-muted);
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s;
  flex-shrink: 0;
}
.session-item:hover .session-delete-btn {
  opacity: 1;
}
.session-delete-btn:hover {
  background: #fee2e2;
  color: #ef4444;
}

.session-empty {
  text-align: center;
  color: var(--ink-muted);
  font-size: 13px;
  padding: 40px 16px;
}

.chat-clear-btn {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 1px;
  color: var(--ink-muted);
  padding: 2px 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}
.chat-clear-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-soft);
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding-right: 8px;
  pointer-events: auto;
}
.chat-messages::-webkit-scrollbar {
  width: 0;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--ink-muted);
  font-size: 14px;
  text-align: center;
  gap: 8px;
  line-height: 1.8;
}

.msg {
  display: flex;
  gap: 10px;
  max-width: 100%;
}
.msg.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}
.msg.assistant {
  align-self: flex-start;
}

.msg-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--glass-mid);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--accent);
  font-size: 14px;
}
.msg.user .msg-avatar {
  background: var(--accent-soft);
}

.msg-body {
  min-width: 0;
}

.msg.user .text {
  color: var(--ink-soft);
  font-size: 14px;
  line-height: 1.6;
  text-align: right;
}
.msg.assistant .text {
  color: var(--ink);
  font-size: 14px;
  line-height: 1.7;
  font-weight: 300;
}

.msg .text :deep(pre) {
  margin: 0.3rem 0;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 0.78rem;
  line-height: 1.45;
  background: var(--surface);
  padding: 0.5rem 0.7rem;
  border: 1px solid var(--border);
}
.msg .text :deep(code) {
  background: var(--accent-soft);
  padding: 0.1rem 0.25rem;
  border-radius: 3px;
  font-size: 0.82em;
  font-family: "Fira Code", "Consolas", monospace;
}
.msg .text :deep(pre code) {
  background: transparent;
  padding: 0;
}
.msg .text :deep(p) {
  margin: 0.1rem 0;
}
.msg .text :deep(p:first-child) {
  margin-top: 0;
}
.msg .text :deep(p:last-child) {
  margin-bottom: 0;
}
.msg .text :deep(ul),
.msg .text :deep(ol) {
  padding-left: 1.2rem;
  margin: 0.15rem 0;
}

/* ── Typing animation ── */
.imm-typing {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
}
.imm-typing .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--accent);
  opacity: 0.4;
  animation: typing-bounce 1.4s infinite ease-in-out;
}
.imm-typing .dot:nth-child(2) {
  animation-delay: 0.2s;
}
.imm-typing .dot:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes typing-bounce {
  0%,
  60%,
  100% {
    transform: translateY(0);
    opacity: 0.4;
  }
  30% {
    transform: translateY(-6px);
    opacity: 1;
  }
}

/* ── Quick Replies ── */
.imm-quick-replies {
  display: flex;
  gap: 8px;
  padding: 8px 0;
  overflow-x: auto;
  pointer-events: auto;
  cursor: grab;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.imm-quick-replies::-webkit-scrollbar {
  display: none;
}

.imm-qr-btn {
  flex-shrink: 0;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--ink-muted);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.imm-qr-btn:hover:not(:disabled) {
  background: var(--accent-soft);
  border-color: var(--accent);
  color: var(--accent);
}
.imm-qr-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ── Input Area ── */
.imm-input-area {
  pointer-events: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.imm-textarea {
  width: 100%;
  box-sizing: border-box;
  border-radius: 12px;
  border: 1px solid var(--border);
  padding: 10px 14px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  min-height: 60px;
  max-height: 100px;
  background: var(--surface);
  color: var(--ink);
  transition: all 0.25s;
}
.imm-textarea:focus {
  outline: none;
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--accent-soft);
  background: var(--surface-hover);
}

.imm-input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.imm-input-tip {
  font-size: 11px;
  color: var(--ink-muted);
}

.imm-send-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: var(--accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: var(--shadow-button);
  transition: all 0.25s;
}
.imm-send-btn:hover:not(:disabled) {
  box-shadow: var(--shadow-button-hover);
  transform: translateY(-1px);
}
.imm-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@keyframes pulse {
  0%,
  100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.3);
    opacity: 0.6;
  }
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .chat-panel {
    width: 100%;
    padding: 60px 16px 120px 16px;
    background: linear-gradient(
      to bottom,
      transparent 0%,
      var(--canvas) 15%,
      var(--canvas) 100%
    );
    -webkit-mask-image: none;
    mask-image: none;
  }

  .video-mini-overlay {
    bottom: auto;
    top: 70px;
    left: 12px;
  }

  .video-mini-wrapper {
    width: 120px;
    height: 90px;
  }

  .mic-wrapper {
    bottom: 100px;
  }

  .wave-container {
    width: 280px;
    height: 120px;
  }
}
</style>
