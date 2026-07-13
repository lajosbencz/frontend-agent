// Mic capture -> mono 16kHz Float32 PCM, the format Whisper expects. getUserMedia requires a
// secure context (https/localhost) - the caller gates on `micSupported()`.
//
// Captures raw PCM directly off the Web Audio graph (ScriptProcessorNode) instead of going
// through MediaRecorder -> Blob -> decodeAudioData. That round-trip forces an encode (browser's
// default opus/webm choice) and a decode of it back, and both steps have real, filed engine bugs
// (Chromium #41290979 "decodeAudioData unable to decode... from a MediaRecorder blob"; Firefox
// #1267248 "MediaRecorder audio quality depends on AudioContext") that can silently degrade or
// blank the result depending on browser/OS/codec - which is exactly the "always transcribes
// nonsense regardless of what was said" symptom this replaces. Grabbing samples straight off the
// graph has no container/codec in the loop at all, so there's nothing there to decode wrong.
// ScriptProcessorNode is deprecated in favor of AudioWorkletNode, but AudioWorklet needs its own
// module file loaded via `audioContext.audioWorklet.addModule(url)` - real added complexity for
// no behavioral difference here. ScriptProcessorNode remains supported in every current browser.

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
// 4096 frames @ 16kHz ~= 256ms per chunk - small enough for a responsive stop(), large enough to
// avoid excessive callback overhead.
const BUFFER_SIZE = 4096

export async function startRecording(): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  // Constructing the context AT the target rate makes the browser resample the live mic input to
  // 16kHz as part of the normal audio graph - no separate manual resample step needed afterward.
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

  // A ScriptProcessorNode only fires onaudioprocess while connected through to the destination -
  // route through a silent (gain 0) node so nothing is audibly played back (no mic-into-speakers
  // feedback) while still keeping the graph "pulled".
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
