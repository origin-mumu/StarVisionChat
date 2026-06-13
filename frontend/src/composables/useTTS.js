/**
 * TTS (Text-to-Speech) Composable
 * Browser-only TTS using SpeechSynthesis API
 * Supports sentence-level queuing and streaming text accumulation
 */
import { ref } from 'vue'

export function useTTS() {
  const ttsEnabled = ref(false)
  const isSpeaking = ref(false)

  let queue = []
  let isProcessing = false
  let buffer = ''

  // Sentence boundary pattern
  const SENTENCE_RE = /[。！？.!?\n]+/

  /**
   * Toggle TTS on/off
   */
  function toggleTTS() {
    ttsEnabled.value = !ttsEnabled.value
    if (!ttsEnabled.value) {
      reset()
    }
  }

  /**
   * Split text into sentences and enqueue each
   */
  function enqueueText(text) {
    if (!ttsEnabled.value || !text) return

    const parts = text.split(SENTENCE_RE).filter(s => s.trim())
    for (const part of parts) {
      queue.push(part.trim())
    }

    if (!isProcessing) {
      processQueue()
    }
  }

  /**
   * Process the TTS queue sequentially
   */
  async function processQueue() {
    if (queue.length === 0) {
      isProcessing = false
      return
    }

    isProcessing = true
    isSpeaking.value = true

    const text = queue.shift()
    if (text) {
      await playViaBrowserTTS(text)
    }

    // Continue with next item
    processQueue()
  }

  /**
   * Play text via browser SpeechSynthesis
   */
  function playViaBrowserTTS(text) {
    return new Promise((resolve) => {
      if (!window.speechSynthesis) {
        resolve()
        return
      }

      // Cancel any ongoing speech
      window.speechSynthesis.cancel()

      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = 'zh-CN'
      utterance.rate = 1.0
      utterance.pitch = 1.0

      utterance.onend = () => {
        if (queue.length === 0) {
          isSpeaking.value = false
        }
        resolve()
      }

      utterance.onerror = () => {
        if (queue.length === 0) {
          isSpeaking.value = false
        }
        resolve()
      }

      window.speechSynthesis.speak(utterance)
    })
  }

  /**
   * Feed streaming text chunks
   * Accumulates in buffer, detects sentence boundaries, enqueues complete sentences
   */
  function feedStreamChunk(chunk) {
    if (!ttsEnabled.value) return

    buffer += chunk

    // Check for sentence boundaries
    const parts = buffer.split(SENTENCE_RE)
    if (parts.length > 1) {
      // All parts except the last are complete sentences
      for (let i = 0; i < parts.length - 1; i++) {
        const sentence = parts[i].trim()
        if (sentence) {
          queue.push(sentence)
        }
      }
      // Keep the remaining partial sentence in buffer
      buffer = parts[parts.length - 1]

      if (!isProcessing) {
        processQueue()
      }
    }
  }

  /**
   * Flush remaining buffer content after stream ends
   */
  function flushStreamBuffer() {
    if (!ttsEnabled.value) return

    const remaining = buffer.trim()
    if (remaining) {
      queue.push(remaining)
      buffer = ''

      if (!isProcessing) {
        processQueue()
      }
    }
  }

  /**
   * Reset all TTS state
   */
  function reset() {
    queue = []
    buffer = ''
    isProcessing = false
    isSpeaking.value = false
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }
  }

  /**
   * Stop playback and clear queue
   */
  function stopAndClear() {
    queue = []
    buffer = ''
    isProcessing = false
    isSpeaking.value = false
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel()
    }
  }

  return {
    ttsEnabled,
    isSpeaking,
    toggleTTS,
    enqueueText,
    feedStreamChunk,
    flushStreamBuffer,
    reset,
    stopAndClear,
    playViaBrowserTTS,
  }
}
