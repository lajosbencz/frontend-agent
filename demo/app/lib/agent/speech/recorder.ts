// Mic capture -> mono 16kHz Float32 PCM (Whisper's format). getUserMedia needs a secure context;
// the caller gates on micSupported().
//
// Captures raw PCM off the Web Audio graph (ScriptProcessorNode) instead of MediaRecorder -> Blob
// -> decodeAudioData: that round-trip's encode/decode has filed engine bugs (Chromium #41290979,
// Firefox #1267248) that can silently blank the audio - the "always transcribes nonsense" symptom.
// ScriptProcessorNode is deprecated but AudioWorklet adds a module file for no behavioral gain here.

export interface Recording {
  /** Stop capture, release the mic, and return mono 16kHz samples. */
  stop(): Promise<Float32Array>
  /** Abandon the take and release the mic without transcribing. */
  cancel(): void
}

export function micSupported(): boolean {
  return typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && typeof AudioContext !== 'undefined'
}

const TARGET_SAMPLE_RATE = 16000
// 4096 frames @ 16kHz ~= 256ms/chunk: responsive stop() without excessive callback overhead.
const BUFFER_SIZE = 4096

export async function startRecording(): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  // Context at the target rate makes the browser resample the mic input to 16kHz in-graph.
  const ctx = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE })
  const source = ctx.createMediaStreamSource(stream)
  const processor = ctx.createScriptProcessor(BUFFER_SIZE, source.channelCount, 1)
  const chunks: Float32Array[] = []

  processor.onaudioprocess = (e) => {
    const input = e.inputBuffer
    if (input.numberOfChannels === 1) {
      chunks.push(input.getChannelData(0).slice())
    } else {
      const l = input.getChannelData(0)
      const r = input.getChannelData(1)
      const mono = new Float32Array(l.length)
      for (let i = 0; i < l.length; i++) mono[i] = (l[i] + r[i]) / 2
      chunks.push(mono)
    }
  }

  // ScriptProcessorNode only fires onaudioprocess while wired to the destination; route through a
  // gain-0 node to keep the graph pulled without playing the mic back through the speakers.
  const silence = ctx.createGain()
  silence.gain.value = 0
  source.connect(processor)
  processor.connect(silence)
  silence.connect(ctx.destination)

  const teardown = () => {
    processor.disconnect()
    source.disconnect()
    silence.disconnect()
    stream.getTracks().forEach((t) => t.stop())
    void ctx.close()
  }

  const concat = (): Float32Array => {
    const total = chunks.reduce((n, c) => n + c.length, 0)
    const out = new Float32Array(total)
    let offset = 0
    for (const c of chunks) {
      out.set(c, offset)
      offset += c.length
    }
    return out
  }

  return {
    stop: async () => {
      processor.onaudioprocess = null
      teardown()
      return concat()
    },
    cancel: () => {
      processor.onaudioprocess = null
      teardown()
    },
  }
}
