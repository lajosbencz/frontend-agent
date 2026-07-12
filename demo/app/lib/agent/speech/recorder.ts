// Mic capture → mono 16kHz Float32 PCM, the format Whisper expects. Uses MediaRecorder for
// capture and an OfflineAudioContext for clean downmix + resample (no manual DSP). getUserMedia
// requires a secure context (https/localhost) - the caller gates on `micSupported()`.

export interface Recording {
  /** Stop capture, release the mic, and return mono 16kHz samples. */
  stop(): Promise<Float32Array>
  /** Abandon the take and release the mic without transcribing. */
  cancel(): void
}

export function micSupported(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== 'undefined'
  )
}

export async function startRecording(): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const recorder = new MediaRecorder(stream)
  const chunks: Blob[] = []
  recorder.ondataavailable = (e) => {
    if (e.data.size) chunks.push(e.data)
  }
  recorder.start()

  const release = () => stream.getTracks().forEach((t) => t.stop())

  return {
    stop: () =>
      new Promise<Float32Array>((resolve, reject) => {
        recorder.onstop = async () => {
          release()
          try {
            resolve(await blobToMono16k(new Blob(chunks, { type: recorder.mimeType })))
          } catch (err) {
            reject(err)
          }
        }
        recorder.stop()
      }),
    cancel: () => {
      recorder.onstop = null
      if (recorder.state !== 'inactive') recorder.stop()
      release()
    },
  }
}

async function blobToMono16k(blob: Blob): Promise<Float32Array> {
  const buf = await blob.arrayBuffer()
  const ctx = new AudioContext()
  const decoded = await ctx.decodeAudioData(buf)
  await ctx.close()
  return resampleTo16k(downmix(decoded), decoded.sampleRate)
}

function downmix(audio: AudioBuffer): Float32Array {
  if (audio.numberOfChannels === 1) return audio.getChannelData(0).slice()
  const l = audio.getChannelData(0)
  const r = audio.getChannelData(1)
  const out = new Float32Array(l.length)
  for (let i = 0; i < l.length; i++) out[i] = (l[i] + r[i]) / 2
  return out
}

async function resampleTo16k(input: Float32Array, srcRate: number): Promise<Float32Array> {
  const TARGET = 16000
  if (srcRate === TARGET) return input
  const frames = Math.max(1, Math.ceil((input.length * TARGET) / srcRate))
  const offline = new OfflineAudioContext(1, frames, TARGET)
  const src = offline.createBuffer(1, input.length, srcRate)
  src.copyToChannel(input, 0)
  const node = offline.createBufferSource()
  node.buffer = src
  node.connect(offline.destination)
  node.start()
  const rendered = await offline.startRendering()
  return rendered.getChannelData(0)
}
