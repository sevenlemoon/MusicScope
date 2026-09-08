export type StemName = "vocals" | "instrumental";

export type StemBuffers = Record<StemName, AudioBuffer>;

export interface AudioContextPort {
  currentTime: number;
  destination: AudioNode;
  createGain: () => GainNode;
  createBufferSource: () => AudioBufferSourceNode;
  resume: () => Promise<void>;
}

export class SynchronizedStemPlayer {
  private readonly context: AudioContextPort;
  private buffers: StemBuffers | null = null;
  private sources: Partial<Record<StemName, AudioBufferSourceNode>> = {};
  private gains: Partial<Record<StemName, GainNode>> = {};
  private gainsByStem: Record<StemName, number> = { vocals: 1, instrumental: 1 };
  private offset = 0;
  private startedAt = 0;
  private playing = false;

  constructor(context: AudioContextPort) {
    this.context = context;
  }

  setBuffers(buffers: StemBuffers): void {
    this.buffers = buffers;
    this.offset = 0;
  }

  get duration(): number {
    if (!this.buffers) return 0;
    return Math.min(this.buffers.vocals.duration, this.buffers.instrumental.duration);
  }

  get isPlaying(): boolean {
    return this.playing;
  }

  get currentTime(): number {
    if (!this.playing) return this.offset;
    return Math.min(this.duration, this.offset + Math.max(0, this.context.currentTime - this.startedAt));
  }

  setGain(stem: StemName, value: number): void {
    const gain = Math.max(0, Math.min(1, value));
    this.gainsByStem[stem] = gain;
    if (this.gains[stem]) this.gains[stem]!.gain.value = gain;
  }

  async play(): Promise<void> {
    if (!this.buffers || this.playing) return;
    if (this.offset >= this.duration) this.offset = 0;
    await this.context.resume();
    const startAt = this.context.currentTime + 0.05;
    (Object.keys(this.buffers) as StemName[]).forEach((stem) => {
      const source = this.context.createBufferSource();
      const gain = this.context.createGain();
      source.buffer = this.buffers![stem];
      gain.gain.value = this.gainsByStem[stem];
      source.connect(gain);
      gain.connect(this.context.destination);
      source.start(startAt, this.offset);
      this.sources[stem] = source;
      this.gains[stem] = gain;
    });
    this.startedAt = startAt;
    this.playing = true;
  }

  pause(): void {
    if (!this.playing) return;
    this.offset = this.currentTime;
    this.stopSources();
    this.playing = false;
  }

  seek(value: number): void {
    const nextOffset = Math.max(0, Math.min(this.duration, value));
    const wasPlaying = this.playing;
    if (wasPlaying) this.stopSources();
    this.offset = nextOffset;
    this.playing = false;
    if (wasPlaying) void this.play();
  }

  destroy(): void {
    this.stopSources();
    this.playing = false;
    this.buffers = null;
  }

  private stopSources(): void {
    (Object.keys(this.sources) as StemName[]).forEach((stem) => {
      try {
        this.sources[stem]?.stop();
      } catch {
        // A source may already have reached its natural end.
      }
    });
    this.sources = {};
    this.gains = {};
  }
}

export async function decodeStemBuffers(context: AudioContext, urls: Record<StemName, string>): Promise<StemBuffers> {
  const load = async (url: string): Promise<AudioBuffer> => {
    const response = await fetch(url);
    if (!response.ok) throw new Error("A separated stem could not be loaded");
    return context.decodeAudioData(await response.arrayBuffer());
  };
  const [vocals, instrumental] = await Promise.all([load(urls.vocals), load(urls.instrumental)]);
  if (Math.abs(vocals.duration - instrumental.duration) > 0.1) {
    throw new Error("Separated stems are not synchronized");
  }
  return { vocals, instrumental };
}
