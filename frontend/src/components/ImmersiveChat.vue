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
import { useSceneStore } from "../stores/sceneStore";
import { wsService } from "../services/wsService";
import { useCamera } from "../composables/useCamera";
import { useMicrophone } from "../composables/useMicrophone";
import { useGesture } from "../composables/useGesture";
import { useThemeStore } from "../stores/themeStore";
import SettingsPanel from "./SettingsPanel.vue";
import MemoryPanel from "./MemoryPanel.vue";
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
  Notebook,
  Search,
  FullScreen,
  ArrowLeft,
  ArrowRight,
  Lock,
} from "@element-plus/icons-vue";

import { useRouter } from "vue-router";

const router = useRouter();

const themeStore = useThemeStore();
const { currentTheme, themes } = storeToRefs(themeStore);
const { setTheme } = themeStore;

const chatStore = useChatStore();
const sessionStore = useSessionStore();
const sceneStore = useSceneStore();
const showSessionList = ref(false);
const showSceneMenu = ref(false);
const showMemoryPanel = ref(false);
const showQrPanel = ref(false);
const lanUrl = ref("");
const cameraSessionId = ref("");
const remoteStream = ref(null);
const useRemoteCamera = ref(false);
const remoteConnecting = ref(false);
const videoMain = ref(false); // false=AI主界面, true=视频主界面
const chatCollapsed = ref(false); // 侧边栏折叠
const memoryNotification = ref("");
const sceneSuggestion = ref(null); // { sceneName }
let sceneMonitorTimer = null;
const SCENE_MONITOR_INTERVAL = 4000; // 8秒检测一次

// 自定义场景
const showAddScene = ref(false);
const newSceneName = ref("");
const newScenePrompt = ref("");

/* ─── Model provider ─── */
const modelProvider = ref("mimo"); // mimo / qwen
let qwenAudioSent = false; // Qwen 模式下是否已发送过音频（Qwen 要求先发音频才能发图像）

// Load model provider from config
function loadModelProvider() {
  const saved = localStorage.getItem("starvisionchat_config");
  if (saved) {
    try {
      const config = JSON.parse(saved);
      modelProvider.value = config.modelProvider || "mimo";
    } catch {
      /* ignore */
    }
  }
}

/* ─── Multi-device QR ─── */
const CAMERA_WS_URL = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api/ws/camera`;
let cameraWs = null;
let cameraPc = null;

function generateSessionId() {
  return "cam_" + Math.random().toString(36).substring(2, 10);
}

async function openQrPanel() {
  if (lanUrl.value) {
    showQrPanel.value = true;
    return;
  }
  try {
    const resp = await fetch("/api/network-info");
    const data = await resp.json();
    if (data.lan_ip && data.lan_ip !== "127.0.0.1") {
      cameraSessionId.value = generateSessionId();
      lanUrl.value = `${data.frontend_url}/#/camera?session=${cameraSessionId.value}`;
      showQrPanel.value = true;
      // 预连接信令通道
      connectCameraSignaling();
    }
  } catch {
    /* ignore */
  }
}

function connectCameraSignaling() {
  if (cameraWs) cameraWs.close();
  cameraWs = new WebSocket(CAMERA_WS_URL);

  cameraWs.onopen = () => {
    cameraWs.send(
      JSON.stringify({
        type: "camera_connect",
        data: { session: cameraSessionId.value },
      }),
    );
  };

  cameraWs.onmessage = async (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === "camera_ready") {
      remoteConnecting.value = true;
    } else if (msg.type === "webrtc_offer") {
      await handleRemoteOffer(msg.data);
    } else if (msg.type === "webrtc_ice") {
      try {
        if (cameraPc)
          await cameraPc.addIceCandidate(new RTCIceCandidate(msg.data));
      } catch {
        /* ignore */
      }
    } else if (msg.type === "camera_disconnect") {
      disconnectRemoteCamera();
    }
  };
}

async function handleRemoteOffer(sdp) {
  closePeerConnection();
  const config = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
  cameraPc = new RTCPeerConnection(config);

  cameraPc.ontrack = (event) => {
    remoteStream.value = event.streams[0];
    useRemoteCamera.value = true;
    remoteConnecting.value = false;
    showQrPanel.value = false;
  };

  cameraPc.onicecandidate = (event) => {
    if (event.candidate && cameraWs?.readyState === WebSocket.OPEN) {
      cameraWs.send(
        JSON.stringify({
          type: "webrtc_ice",
          data: {
            session: cameraSessionId.value,
            candidate: event.candidate.toJSON(),
          },
        }),
      );
    }
  };

  cameraPc.onconnectionstatechange = () => {
    if (
      cameraPc &&
      (cameraPc.connectionState === "failed" ||
        cameraPc.connectionState === "disconnected")
    ) {
      disconnectRemoteCamera();
    }
  };

  await cameraPc.setRemoteDescription(new RTCSessionDescription(sdp));
  const answer = await cameraPc.createAnswer();
  await cameraPc.setLocalDescription(answer);
  cameraWs.send(
    JSON.stringify({
      type: "webrtc_answer",
      data: { session: cameraSessionId.value, sdp: answer },
    }),
  );
}

function closePeerConnection() {
  if (cameraPc) {
    cameraPc.close();
    cameraPc = null;
  }
}

function disconnectRemoteCamera() {
  closePeerConnection();
  remoteStream.value = null;
  useRemoteCamera.value = false;
  remoteConnecting.value = false;
  if (cameraWs) {
    cameraWs.close();
    cameraWs = null;
  }
}

onBeforeUnmount(() => {
  disconnectRemoteCamera();
  // ... existing cleanup
});

onMounted(() => {
  loadModelProvider();

  // 监听配置更新事件（从设置面板触发）
  window.addEventListener("config-updated", loadModelProvider);
});

onBeforeUnmount(() => {
  window.removeEventListener("config-updated", loadModelProvider);
});

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

// 手势识别 — 检测逻辑已合并到场景监控，这里只管理锁定状态
const gesture = useGesture();

// 手势锁定 → 同步到场景自动切换
watch(() => gesture.isLocked.value, (locked) => {
  sceneStore.isAutoSwitchEnabled = !locked;
});

// 远程摄像头：切换到手机的 video 流
watch(remoteStream, (stream) => {
  if (stream && videoRef.value) {
    stopCameraFn();
    videoRef.value.srcObject = stream;
    videoRef.value.play().catch(() => {});
  } else if (!stream && videoRef.value && !isCameraOn.value) {
    initCamera();
  }
});

async function toggleCamera() {
  if (isCameraOn.value) {
    stopCameraFn();
    stopSceneMonitor();
  } else {
    cameraLoading.value = true;
    await initCamera();
    cameraLoading.value = false;
    startSceneMonitor();
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

/* ─── 连续对话模式 ─── */
const continuousMode = ref(true); // AI说完后自动开始录音

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
let qwenProcessor = null; // Qwen 模式 ScriptProcessorNode
let qwenMicStream = null; // Qwen 模式麦克风 MediaStream
let recordingMimeType = "audio/webm";
let abortCtrl = null;

const SILENCE_THRESHOLD = 0.008;
const SILENCE_TIMEOUT_MS = 1400;

function initSpeech() {
  speechSupported.value = !!navigator.mediaDevices?.getUserMedia;
}

/** AI说完话后自动触发语音录入（连续对话） */
let autoVoiceTimer = null;
function autoContinueVoice() {
  if (!continuousMode.value) return;
  if (autoVoiceTimer) { clearTimeout(autoVoiceTimer); autoVoiceTimer = null }
  autoVoiceTimer = setTimeout(() => {
    autoVoiceTimer = null;
    // 再次检查状态，防止竞态
    if (currentMode.value !== "idle") return;
    if (!speechSupported.value) return;
    toggleVoice();
  }, 600);
}

async function toggleVoice() {
  if (currentMode.value === "thinking" || currentMode.value === "speaking")
    return;
  if (!speechSupported.value) return;

  // 用户手动点击语音按钮时，取消自动触发
  if (autoVoiceTimer) { clearTimeout(autoVoiceTimer); autoVoiceTimer = null }

  // 重新加载模型配置（可能在设置面板中被修改）
  const saved = localStorage.getItem("starvisionchat_config");
  if (saved) {
    try {
      const config = JSON.parse(saved);
      modelProvider.value = config.modelProvider || "mimo";
    } catch {
      /* ignore */
    }
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

    if (modelProvider.value === "qwen") {
      // ── Qwen 模式：实时 PCM 流式发送 ──
      await startQwenRealtimeRecording(stream);
    } else {
      // ── MiMo 模式：MediaRecorder 录音结束后一次性发送 ──
      await startMimoRecording(stream);
    }
  } catch {
    interimText.value = "麦克风权限被拒绝";
    setMode("idle");
  }
}

/** Qwen 模式：实时 PCM 流式录制，每 256 样本发送一次音频+图像 */
async function startQwenRealtimeRecording(stream) {
  qwenMicStream = stream;
  audioCtx = new AudioContext({ sampleRate: 16000 });
  const source = audioCtx.createMediaStreamSource(stream);
  // bufferSize=256 → 每 16ms 一帧（16000/256），实时性好
  qwenProcessor = audioCtx.createScriptProcessor(256, 1, 1);
  source.connect(qwenProcessor);
  qwenProcessor.connect(audioCtx.destination);

  let lastImgTime = 0;
  qwenAudioSent = false;

  qwenProcessor.onaudioprocess = (e) => {
    if (currentMode.value !== "listening") return;
    const samples = e.inputBuffer.getChannelData(0);
    // float32 → int16
    const pcm = new ArrayBuffer(samples.length * 2);
    const view = new DataView(pcm);
    for (let i = 0; i < samples.length; i++) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    wsService.send("audio_stream", { audio: arrayBufToB64(pcm) });
    qwenAudioSent = true;

    // 每秒发送一帧图像
    const now = Date.now();
    if (now - lastImgTime >= 1000) {
      lastImgTime = now;
      const frame = captureFrame();
      if (frame) wsService.send("image_stream", { image: frame });
    }
  };

  // 静音检测（复用同一逻辑）
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 256;
  analyser.smoothingTimeConstant = 0.3;
  source.connect(analyser);
  checkSilence();
}

/** MiMo 模式：MediaRecorder 录音，结束后一次性发送 */
async function startMimoRecording(stream) {
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
    await sendVoiceAudio(audioBlob);
  };

  mediaRecorder.onerror = () => {
    setMode("idle");
  };
  mediaRecorder.start(100);
  checkSilence();
}

function checkSilence() {
  // Qwen 模式用 qwenProcessor，MiMo 模式用 mediaRecorder
  const isRecording =
    qwenProcessor || (mediaRecorder && mediaRecorder.state === "recording");
  if (!analyser || currentMode.value !== "listening" || !isRecording) return;

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
  if (qwenProcessor) {
    // Qwen 模式：断开 ScriptProcessorNode
    qwenProcessor.disconnect();
    qwenProcessor = null;
    if (qwenMicStream) {
      qwenMicStream.getTracks().forEach((t) => t.stop());
      qwenMicStream = null;
    }
    if (audioCtx) {
      audioCtx.close();
      audioCtx = null;
    }
    analyser = null;
    // 通知后端：录音结束，提交缓冲区并请求模型响应
    wsService.send("audio_end_qwen", {});
    setMode("thinking");
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
    const wav = await convertToWav(audioBlob);
    const b64 = arrayBufToB64(await wav.arrayBuffer());

    // 捕获当前摄像头帧
    const frame = captureFrame();

    // Send audio via WebSocket（附带当前帧）
    setMode("thinking");
    wsService.sendAudioChunk(b64);
    wsService.sendAudioEnd(frame);
  } catch {
    setMode("idle");
  }
}

/* ─── Session Management ─── */
function createNewSession() {
  sessionStore.createSession();
  chatStore.loadSession([]);
  showSessionList.value = false;
}

function switchToSession(id) {
  const messages = sessionStore.switchSession(id);
  chatStore.loadSession(messages);
  showSessionList.value = false;
}

function deleteSession(id) {
  sessionStore.deleteSession(id);
  // 如果删除后当前会话变了，加载新当前会话的消息
  if (sessionStore.currentSessionId !== id) {
    chatStore.loadSession(sessionStore.currentMessages);
  }
}

function formatSessionTime(date) {
  if (!date) return "";
  const d = date instanceof Date ? date : new Date(date);
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  if (isToday) {
    return d.toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }
  return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric" });
}

/* ─── Scene Management ─── */
function switchScene(sceneId) {
  sceneStore.switchScene(sceneId);
  showSceneMenu.value = false;

  // 通知后端更新系统提示词
  wsService.send("scene_update", {
    system_prompt: sceneStore.systemPrompt,
  });
}

function handleAddScene() {
  if (!newSceneName.value.trim() || !newScenePrompt.value.trim()) return;
  sceneStore.addCustomScene(
    newSceneName.value.trim(),
    newScenePrompt.value.trim(),
  );
  newSceneName.value = "";
  newScenePrompt.value = "";
  showAddScene.value = false;
}

function handleRemoveScene(sceneId) {
  sceneStore.removeCustomScene(sceneId);
}

// 自动检测场景切换
function checkAutoSwitch(text) {
  const suggestedScene = sceneStore.detectScene(text);
  if (suggestedScene) {
    switchScene(suggestedScene);
  }
}

/* ─── Scene Monitor（定时截帧检测场景变化） ─── */
function startSceneMonitor() {
  stopSceneMonitor();
  sceneMonitorTimer = setInterval(() => {
    if (!isCameraOn.value && !remoteStream.value) return;
    const frame = captureFrame();
    if (frame) {
      wsService.send("scene_monitor", {
        image: frame,
        scenes: sceneStore.scenes.map((s) => ({ id: s.id, name: s.name })),
        current_scene: sceneStore.currentScene.name,
        is_locked: gesture.isLocked.value,
      });
    }
  }, SCENE_MONITOR_INTERVAL);
}

function stopSceneMonitor() {
  if (sceneMonitorTimer) {
    clearInterval(sceneMonitorTimer);
    sceneMonitorTimer = null;
  }
}

function handleSceneDetected(data) {
  const sceneId = data.scene;
  const sceneName = data.name || "";
  if (!sceneId || sceneId === sceneStore.currentSceneId) return;
  // 自动切换
  switchScene(sceneId);
  // 显示切换通知（3秒后消失）
  sceneSuggestion.value = { sceneName };
  setTimeout(() => {
    sceneSuggestion.value = null;
  }, 3000);
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
      // 自动检测场景切换
      checkAutoSwitch(text);

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
      autoContinueVoice();
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
let qwenTextBuffer = ""; // 缓冲 AI 文本，等用户转录显示后再显示
let qwenTranscriptReceived = false; // 是否已收到用户转录

function handleQwenTextDelta(data) {
  // 流式追加文本到当前 AI 回复
  const text = data.text || "";
  if (!text) return;

  // 如果用户转录还没显示，先缓冲
  if (!qwenTranscriptReceived) {
    qwenTextBuffer += text;
    return;
  }

  // 找到最后一条 AI 消息并追加
  const messages = chatStore.messages;
  const lastMsg = messages[messages.length - 1];
  if (lastMsg && !lastMsg.isUser) {
    lastMsg.text += text;
  } else {
    chatStore.addMessage(text, false);
  }
}

// 刷新缓冲的 AI 文本
function flushQwenTextBuffer() {
  if (!qwenTextBuffer) return;

  const messages = chatStore.messages;
  const lastMsg = messages[messages.length - 1];
  if (lastMsg && !lastMsg.isUser) {
    lastMsg.text += qwenTextBuffer;
  } else {
    chatStore.addMessage(qwenTextBuffer, false);
  }
  qwenTextBuffer = "";
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
    autoContinueVoice();
    return;
  }

  qwenIsPlaying = true;
  setMode("speaking");

  if (!qwenAudioContext) {
    qwenAudioContext = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 24000,
    });
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

let qwenTurnInputLen = 0; // 本轮用户输入字符数

function handleQwenTranscript(data) {
  // 用户语音转录完成
  const text = data.text || "";
  if (text) {
    // 自动检测场景切换
    checkAutoSwitch(text);

    // 标记已收到用户转录
    qwenTranscriptReceived = true;

    // 先显示用户消息
    chatStore.addMessage(text, true);
    scrollChat();

    // 记录输入长度用于 token 估算
    qwenTurnInputLen = text.length;

    // 然后刷新缓冲的 AI 文本
    flushQwenTextBuffer();
  }
}

function handleQwenResponseDone() {
  // Qwen 响应完成 — 估算 token 用量
  const outputLen = qwenTextBuffer.length;
  const estimatedTokens = Math.ceil((qwenTurnInputLen + outputLen) * 1.5);
  chatStore.updateCost({
    stt_calls: chatStore.costData.stt_calls + 1,
    llm_tokens: chatStore.costData.llm_tokens + estimatedTokens,
  });
  qwenTurnInputLen = 0;
  qwenIsPlaying = false;
  qwenTranscriptReceived = false;
  qwenTextBuffer = "";
  setMode("idle");
}

function handleMemorySaved(data) {
  // 记忆保存通知
  memoryNotification.value = data.message || "已保存到记忆";
  setTimeout(() => {
    memoryNotification.value = "";
  }, 3000);
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
      setTimeout(() => {
        setMode("idle");
        // 文本模式无音频时，也触发连续对话
        autoContinueVoice();
      }, 1500);
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

  // 自动检测场景切换
  checkAutoSwitch(text);

  chatStore.addMessage(text, true);

  // 捕获当前摄像头帧，和消息一起发送
  const frame = captureFrame();
  wsService.sendTextInput(text, frame);

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

function takeSnapshot() {
  if (!isCameraOn.value) return;
  const frame = captureFrame();
  if (!frame) return;
  // 发送截图分析请求
  wsService.send("text_input", {
    text: "请详细描述你看到的画面内容",
    image: frame,
  });
  chatStore.addMessage("请详细描述你看到的画面内容", true);
  setMode("thinking");
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
let SPHERE_RADIUS = 180;
const PARTICLE_COUNT = 300;
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
  const cool = getThemeColor("--cool", "#5CADCA");
  return {
    accent,
    warm,
    cool,
    void: dark ? "rgba(255,255,255,0.12)" : `${cool}30`,
    star: dark ? "rgba(255,255,255,0.5)" : `${accent}88`,
    // 每种模式用不同主色调，拉开层次
    idle: accent,
    listening: accent,
    thinking: warm,
    speaking: cool,
  };
}

function hexToRGB(hex) {
  const h = hex.replace("#", "");
  return {
    r: parseInt(h.substring(0, 2), 16),
    g: parseInt(h.substring(2, 4), 16),
    b: parseInt(h.substring(4, 6), 16),
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
  // 给已有粒子重新分配新主题的三色
  if (orbParticles) {
    const palette = [themeColors.accent, themeColors.warm, themeColors.cool];
    orbParticles.forEach((p) => {
      if (p.type === "theme") {
        p.color = palette[Math.floor(Math.random() * 3)];
      } else {
        p.color = themeColors.void;
      }
    });
  }
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
    // 20% 半透明点缀 + 80% 从主题三色中随机分配
    const rnd = Math.random();
    if (rnd < 0.2) {
      this.type = "void";
      this.color = themeColors.void;
    } else {
      this.type = "theme";
      // 每个粒子固定一种主题色，三种色均匀分布
      const palette = [themeColors.accent, themeColors.warm, themeColors.cool];
      this.color = palette[Math.floor(Math.random() * 3)];
    }
    this.size = Math.random() * 2.5 + 1.0;
    this.x = 0;
    this.y = 0;
    this.z = 0;
  }

  update(time, rx, ry, mode) {
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
    const accentRGB = hexToRGB(themeColors.accent);
    const warmRGB = hexToRGB(themeColors.warm);
    const coolRGB = hexToRGB(themeColors.cool);
    const colors = [
      { ...accentRGB, radius: orbSize * 1.3, offset: 0, dist: 12 },
      { ...coolRGB, radius: orbSize * 1.2, offset: 2.1, dist: 18 },
      { ...warmRGB, radius: orbSize * 1.4, offset: 4.2, dist: 10 },
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
    grad.addColorStop(0.1, themeColors.accent);
    grad.addColorStop(0.5, themeColors.warm);
    grad.addColorStop(0.9, themeColors.cool);
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
  // 小窗模式下不自动调整尺寸
  if (videoMain.value) return;
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
  chatStore.loadSession(sessionStore.currentMessages);

  orbParticles = Array.from({ length: PARTICLE_COUNT }, () => new OrbP());
  resizeMain();
  resizeWave();
  window.addEventListener("resize", resizeMain);
  window.addEventListener("resize", resizeWave);
  animId = requestAnimationFrame(animate);
  initSpeech();

  // 自动开启摄像头（让用户可以立即与 AI 视觉交互）
  setTimeout(async () => {
    await initCamera();
    startSceneMonitor();
  }, 500);

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
  wsService.on("memory_saved", handleMemorySaved);
  wsService.on("scene_detected", handleSceneDetected);
  wsService.on("gesture_result", (data) => gesture.handleResult(data.result));
});


onBeforeUnmount(() => {
  cancelAnimationFrame(animId);
  window.removeEventListener("resize", resizeMain);
  window.removeEventListener("resize", resizeWave);
  themeObserver.disconnect();
  if (silenceTimer) clearTimeout(silenceTimer);
  if (typewriterTimer) clearInterval(typewriterTimer);
  if (autoVoiceTimer) { clearTimeout(autoVoiceTimer); autoVoiceTimer = null; }
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
  wsService.off("memory_saved", handleMemorySaved);
  wsService.off("scene_detected", handleSceneDetected);
  wsService.off("gesture_result", (data) => gesture.handleResult(data.result));
  stopSceneMonitor();
  wsService.off("qwen_response_done", handleQwenResponseDone);

  // Qwen audio cleanup
  if (qwenAudioContext) {
    qwenAudioContext.close();
    qwenAudioContext = null;
  }
});

watch(
  () => chatStore.messages.length,
  () => scrollChat(),
);

// 切换主/小窗时重置 canvas 尺寸、球半径、重建粒子
watch(videoMain, (isMain) => {
  nextTick(() => {
    const c = mainCanvasRef.value;
    if (!c) return;
    if (isMain) {
      c.width = 200;
      c.height = 150;
      width = 200;
      height = 150;
      SPHERE_RADIUS = 60;
    } else {
      width = window.innerWidth;
      height = window.innerHeight;
      c.width = width;
      c.height = height;
      SPHERE_RADIUS = 260;
    }
    // 重建粒子以适配新半径
    const palette = [themeColors.accent, themeColors.warm, themeColors.cool];
    orbParticles = Array.from({ length: PARTICLE_COUNT }, () => new OrbP());
  });
});
</script>

<template>
  <div class="immersive-overlay">
    <!-- Glow background -->
    <div
      class="glow-bg"
      :style="{ backgroundColor: modeColorMap[currentMode] || '#ef4444' }"
    ></div>

    <!-- Memory notification -->
    <transition name="fade">
      <div v-if="memoryNotification" class="memory-toast">
        <el-icon><Notebook /></el-icon>
        <span>{{ memoryNotification }}</span>
      </div>
    </transition>

    <!-- Gesture hint toast -->
    <transition name="fade">
      <div v-if="gesture.gestureHint.value" class="gesture-toast">
        <span>{{ gesture.gestureHint.value }}</span>
      </div>
    </transition>

    <!-- Scene auto-switch notification -->
    <transition name="fade">
      <div v-if="sceneSuggestion" class="scene-toast">
        <el-icon><VideoCamera /></el-icon>
        <span>已切换到{{ sceneSuggestion.sceneName }}</span>
      </div>
    </transition>

    <!-- Main particle canvas -->
    <canvas
      ref="mainCanvasRef"
      :class="videoMain ? 'mini-canvas' : 'main-canvas'"
      @mousedown="onDown"
      @mousemove="onMove"
      @mouseup="onUp"
      @mouseleave="onUp"
      @touchstart.prevent="onDown"
      @touchmove.prevent="onMove"
      @touchend="onUp"
    ></canvas>
    <!-- AI canvas expand button (shown when video is main) -->
    <div
      v-if="videoMain"
      class="ai-mini-badge"
      @click="videoMain = false"
      title="切换到 AI 主界面"
    >
      <el-icon><Star /></el-icon>
    </div>

    <!-- Top bar: brand + theme dots + settings -->
    <div class="top-bar">
      <div class="top-brand">
        <el-icon :size="18" color="var(--accent)"><Star /></el-icon>
        <span class="top-brand-name">StarVision</span>
        <span class="model-badge" :class="modelProvider">
          {{ modelProvider === "qwen" ? "Qwen" : "MiMo" }}
        </span>

        <!-- Scene indicator -->
        <div class="scene-indicator" @click="showSceneMenu = !showSceneMenu">
          <span
            class="scene-dot"
            :style="{ backgroundColor: sceneStore.currentScene.color }"
          ></span>
          <span class="scene-name">{{ sceneStore.currentScene.name }}</span>
          <span v-if="gesture.isLocked.value" class="lock-badge" title="场景已锁定，不会自动切换"><el-icon><Lock /></el-icon></span>
        </div>
      </div>
      <div class="top-actions">
        <!-- Scene menu -->
        <Transition name="ui-fade">
          <div v-if="showSceneMenu" class="scene-menu glass-mid">
            <div class="scene-menu-header">
              <span>场景模式</span>
              <label class="auto-switch-toggle">
                <input
                  type="checkbox"
                  v-model="sceneStore.isAutoSwitchEnabled"
                />
                <span>自动切换</span>
              </label>
              <label class="auto-switch-toggle" title="AI说完后自动开始语音录入">
                <input
                  type="checkbox"
                  v-model="continuousMode"
                />
                <span>连续对话</span>
              </label>
            </div>
            <div class="scene-list">
              <div
                v-for="scene in sceneStore.scenes"
                :key="scene.id"
                class="scene-item"
                :class="{ active: scene.id === sceneStore.currentSceneId }"
                @click="switchScene(scene.id)"
              >
                <span
                  class="scene-item-dot"
                  :style="{ backgroundColor: scene.color }"
                ></span>
                <div class="scene-item-info">
                  <div class="scene-item-name">{{ scene.name }}</div>
                  <div class="scene-item-desc">{{ scene.description }}</div>
                </div>
                <el-icon
                  v-if="scene.isCustom"
                  class="scene-delete-btn"
                  @click.stop="handleRemoveScene(scene.id)"
                >
                  <Delete />
                </el-icon>
              </div>
              <!-- 添加场景 -->
              <div class="scene-item add-scene" @click="showAddScene = true">
                <el-icon><Plus /></el-icon>
                <span>添加场景</span>
              </div>
            </div>

            <!-- 添加场景对话框 -->
            <div v-if="showAddScene" class="add-scene-dialog">
              <input
                v-model="newSceneName"
                placeholder="场景名称（如：做饭助手）"
                class="add-scene-input"
              />
              <textarea
                v-model="newScenePrompt"
                placeholder="系统提示词（如：你是一位做菜助手...）"
                class="add-scene-textarea"
                rows="3"
              ></textarea>
              <div class="add-scene-actions">
                <button class="add-scene-cancel" @click="showAddScene = false">
                  取消
                </button>
                <button class="add-scene-confirm" @click="handleAddScene">
                  添加
                </button>
              </div>
            </div>
          </div>
        </Transition>

        <!-- Multi-device QR -->
        <button
          class="top-qr-btn"
          :class="{ active: useRemoteCamera }"
          @click="useRemoteCamera ? disconnectRemoteCamera() : openQrPanel()"
          :title="useRemoteCamera ? '点击断开手机摄像头' : '手机扫码打开'"
        >
          <el-icon v-if="useRemoteCamera"><FullScreen /></el-icon>
          <span>{{ useRemoteCamera ? "手机摄像头" : "调用手机相机" }}</span>
        </button>
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
        <!-- Back to Config -->
        <button
          class="top-back-btn"
          @click="router.push('/config')"
          title="返回配置"
        >
          <el-icon><ArrowLeft /></el-icon>
        </button>
        <!-- Chat panel toggle -->
        <button
          class="top-toggle-btn"
          @click="chatCollapsed = !chatCollapsed"
          :title="chatCollapsed ? '展开对话' : '收起对话'"
        >
          <span v-if="chatCollapsed">&laquo;</span>
          <span v-else>&raquo;</span>
        </button>
      </div>
    </div>

    <!-- Memory Panel -->
    <div
      v-if="showMemoryPanel"
      class="memory-panel-wrapper"
      @click.self="showMemoryPanel = false"
    >
      <MemoryPanel @close="showMemoryPanel = false" />
    </div>

    <!-- QR Code Panel -->
    <div
      v-if="showQrPanel"
      class="qr-overlay"
      @click.self="showQrPanel = false"
    >
      <div class="qr-card glass-top">
        <div class="qr-card-header">
          <span>手机扫码打开</span>
          <button class="btn-icon" @click="showQrPanel = false">
            <el-icon><Close /></el-icon>
          </button>
        </div>
        <p class="qr-card-desc">
          手机和电脑连同一 WiFi，扫码后在手机上打开，手机会自动建立摄像头连接。
          如果页面长时间加载请刷新页面重试
        </p>
        <div v-if="remoteConnecting" class="qr-connecting">
          <el-icon class="spin"><Loading /></el-icon>
          <span>等待手机连接...</span>
        </div>
        <img
          v-else
          class="qr-card-img"
          :src="`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(lanUrl)}`"
          alt="手机扫码访问"
        />
        <span class="qr-card-url">{{ lanUrl }}</span>
        <button
          class="btn-skip"
          style="margin-top: 12px"
          @click="showQrPanel = false"
        >
          取消
        </button>
      </div>
    </div>

    <!-- Video stream overlay -->
    <div :class="videoMain ? 'video-main-overlay' : 'video-mini-overlay'">
      <div :class="videoMain ? 'video-main-wrapper' : 'video-mini-wrapper'">
        <video
          ref="videoRef"
          autoplay
          muted
          playsinline
          :class="videoMain ? 'video-main-element' : 'video-mini-element'"
        />
        <div v-if="!isCameraOn" class="video-mini-placeholder">
          <el-icon :size="videoMain ? 48 : 24"><VideoCamera /></el-icon>
        </div>
        <!-- Speaking indicator -->
        <div v-if="isMicSpeaking" class="video-mini-speaking">
          <div class="pulse-ring"></div>
        </div>
        <!-- Switch to mini button (shown when video is main) -->
        <button
          v-if="videoMain"
          class="video-switch-btn"
          @click="videoMain = false"
          title="切换到 AI 主界面"
        >
          <el-icon><Star /></el-icon>
        </button>
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
        <!-- <button
          class="mini-ctrl-btn"
          @click="takeSnapshot"
          title="画面分析"
          :disabled="!isCameraOn"
        >
          <el-icon><Search /></el-icon>
        </button> -->
        <button
          v-if="!videoMain"
          class="mini-ctrl-btn"
          @click="videoMain = true"
          title="视频为主界面"
        >
          <el-icon><FullScreen /></el-icon>
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
      <div
        v-if="showSessionList"
        class="session-sidebar"
        @click.self="showSessionList = false"
      >
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
                <div class="session-time">
                  {{ formatSessionTime(session.updatedAt) }}
                </div>
              </div>
              <button
                class="session-delete-btn"
                @click.stop="deleteSession(session.id)"
                title="删除会话"
              >
                <el-icon><Delete /></el-icon>
              </button>
            </div>
            <div
              v-if="sessionStore.sessions.length === 0"
              class="session-empty"
            >
              暂无会话
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Chat panel (right side) -->
    <div class="chat-panel" :class="{ collapsed: chatCollapsed }">
      <div class="chat-header">
        <button
          class="session-menu-btn"
          @click="showSessionList = !showSessionList"
          title="会话列表"
        >
          <el-icon><ChatDotRound /></el-icon>
          <span class="session-count">{{ sessionStore.sessions.length }}</span>
        </button>
        <button
          class="session-menu-btn"
          :class="{ active: showMemoryPanel }"
          @click="showMemoryPanel = !showMemoryPanel"
          title="AI 记忆"
        >
          <el-icon><Notebook /></el-icon>
        </button>
        <!-- <span>STARVISION CHAT</span> -->
        <div class="cost-badge" title="API 调用成本">
          <span class="cost-label">Tokens</span>
          <span class="cost-value">{{ chatStore.costData.llm_tokens }}</span>
        </div>
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

/* AI canvas as mini view */
.mini-canvas {
  display: block;
  position: absolute;
  bottom: 40px;
  left: 24px;
  width: 200px;
  height: 150px;
  z-index: 30;
  border-radius: 16px;
  border: 1px solid var(--border);
  box-shadow: var(--shadow-card);
  cursor: grab;
  background: var(--canvas-deep);
}
.ai-mini-badge {
  position: absolute;
  bottom: 196px;
  left: 24px;
  z-index: 31;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--glass-bright);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--accent);
  box-shadow: var(--shadow-card);
  transition: all 0.2s;
}
.ai-mini-badge:hover {
  transform: scale(1.1);
}

/* Video as main view */
.video-main-overlay {
  position: absolute;
  inset: 0;
  padding: 60px;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
}
.video-main-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  background: #000;
  border-radius: 20px;
  overflow: hidden;
  border: 2px solid var(--border);
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(255, 255, 255, 0.05);
}
.video-main-element {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.video-switch-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(0, 0, 0, 0.4);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(8px);
}
.video-switch-btn:hover {
  background: rgba(0, 0, 0, 0.6);
  border-color: var(--accent);
  color: var(--accent);
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
  color: #3b7dd8;
}

/* Scene indicator */
.scene-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 999px;
  background: var(--surface);
  border: 1px solid var(--border);
  cursor: pointer;
  transition: all 0.2s;
  margin-left: 8px;
}

.scene-indicator:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.scene-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.scene-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
}

/* Scene menu */
.scene-menu {
  position: absolute;
  top: calc(100% + 12px);
  left: 0;
  width: 280px;
  padding: 16px;
  border-radius: 16px;
  background: var(--glass-mid);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 0.5px solid var(--glass-border);
  box-shadow: var(--shadow-card);
  z-index: 100;
}

.scene-menu-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}

.auto-switch-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--ink-muted);
  cursor: pointer;
}

.auto-switch-toggle input {
  width: 14px;
  height: 14px;
  cursor: pointer;
}

.scene-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.scene-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.scene-item:hover {
  background: var(--surface-hover);
}

.scene-item.active {
  background: var(--accent-soft);
  border: 1px solid var(--accent);
}

.scene-item-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.scene-item-info {
  flex: 1;
  min-width: 0;
}

.scene-item-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}

.scene-item-desc {
  font-size: 11px;
  color: var(--ink-muted);
  margin-top: 2px;
}
.scene-delete-btn {
  opacity: 0;
  cursor: pointer;
  color: var(--ink-muted);
  transition: opacity 0.2s;
}
.scene-item:hover .scene-delete-btn {
  opacity: 0.6;
}
.scene-delete-btn:hover {
  opacity: 1 !important;
  color: #e74c3c;
}
.add-scene {
  justify-content: center;
  gap: 6px;
  opacity: 0.5;
  font-size: 12px;
  border-top: 1px solid var(--border);
  margin-top: 4px;
  padding-top: 8px;
}
.add-scene:hover {
  opacity: 1;
  color: var(--accent);
}

/* Add scene dialog */
.add-scene-dialog {
  padding: 8px;
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.add-scene-input,
.add-scene-textarea {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--glass-base);
  color: var(--ink);
  font-size: 12px;
  font-family: inherit;
  outline: none;
  resize: none;
  box-sizing: border-box;
}
.add-scene-input:focus,
.add-scene-textarea:focus {
  border-color: var(--accent);
}
.add-scene-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}
.add-scene-cancel,
.add-scene-confirm {
  padding: 4px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  font-family: inherit;
}
.add-scene-cancel {
  background: transparent;
  color: var(--ink-muted);
}
.add-scene-confirm {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
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
  width: 360px;
  height: 270px;
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
  background: var(--glass-mid);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 0.5px solid var(--glass-border);
  border-radius: 16px;
  box-shadow: var(--shadow-card);
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
.top-toggle-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--ink-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 18px;
  font-weight: bold;
  line-height: 1;
  font-family: inherit;
}
.top-toggle-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-soft);
}

.top-back-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--ink-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}
.top-back-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-soft);
}

.top-qr-btn {
  height: 28px;
  padding: 0 10px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--ink-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 12px;
  white-space: nowrap;
}
.top-qr-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-soft);
}
.top-qr-btn.active {
  color: #fff;
  background: rgba(76, 175, 80, 0.85);
  border-color: rgba(76, 175, 80, 0.6);
}
.top-qr-btn.active:hover {
  color: #fff;
  background: rgba(244, 67, 54, 0.85);
  border-color: rgba(244, 67, 54, 0.6);
}

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
  transition: transform 0.3s ease;
  background: var(--glass-mid);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-left: 0.5px solid var(--glass-border);
}
.chat-panel.collapsed {
  transform: translateX(100%);
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
.session-menu-btn:hover,
.session-menu-btn.active {
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

.cost-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--glass-base);
  border: 1px solid var(--border);
  opacity: 0.7;
  transition: opacity 0.2s;
}
.cost-badge:hover {
  opacity: 1;
}
.cost-label {
  color: var(--ink-muted);
}
.cost-value {
  color: var(--accent);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
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
  background: rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(2px);
}

.session-sidebar-inner {
  width: 300px;
  height: 100%;
  background: var(--surface);
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 20px rgba(0, 0, 0, 0.1);
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
    background: var(--glass-mid);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-left: none;
  }

  .video-mini-overlay {
    bottom: auto;
    top: 70px;
    left: 12px;
  }

  .video-main-overlay {
    padding: 12px;
  }
  .video-main-wrapper {
    border-radius: 12px;
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

/* Memory Panel */
.memory-panel-wrapper {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
  background: rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(2px);
}

/* Memory Toast */
.memory-toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--glass-bright);
  backdrop-filter: blur(16px);
  border: 1px solid var(--border);
  border-radius: 12px;
  font-size: 14px;
  color: var(--accent);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  animation: toast-in 0.3s ease;
}
@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

/* Gesture Toast */
.gesture-toast {
  position: fixed;
  top: 60px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2000;
  padding: 8px 18px;
  background: var(--accent);
  color: #fff;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  animation: toast-in 0.3s ease;
}

/* Lock Badge */
.lock-badge {
  font-size: 12px;
  margin-left: 4px;
  cursor: default;
}

.fade-enter-active {
  transition: opacity 0.3s;
}
.fade-leave-active {
  transition: opacity 0.5s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Scene Toast */
.scene-toast {
  position: fixed;
  top: 60px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--glass-bright);
  backdrop-filter: blur(16px);
  border: 1px solid var(--accent);
  border-radius: 12px;
  font-size: 13px;
  color: var(--accent);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  animation: toast-in 0.3s ease;
  white-space: nowrap;
}

/* QR Code Panel */
.qr-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(4px);
}

.qr-card {
  text-align: center;
  padding: 28px 32px;
  border-radius: 20px;
  max-width: 340px;
  animation: qr-in 0.25s ease;
}

@keyframes qr-in {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.qr-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
}

.qr-card-desc {
  font-size: 13px;
  color: var(--ink-muted);
  margin: 0 0 20px;
  line-height: 1.6;
}

.qr-card-img {
  width: 200px;
  height: 200px;
  border-radius: 10px;
  display: block;
  margin: 0 auto 12px;
}

.qr-card-url {
  font-size: 12px;
  color: var(--ink-soft);
  font-family: "Consolas", monospace;
  word-break: break-all;
}

.qr-connecting {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px 0;
  color: var(--accent);
  font-size: 14px;
}

.btn-skip {
  padding: 6px 16px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--ink-muted);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-skip:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-soft);
}
</style>
