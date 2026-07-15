export async function detectWebGPU(): Promise<boolean> {
  try {
    const gpu = (navigator as unknown as { gpu?: { requestAdapter?: () => Promise<unknown> } }).gpu
    if (!gpu?.requestAdapter) return false
    return (await gpu.requestAdapter()) != null
  } catch {
    return false
  }
}
