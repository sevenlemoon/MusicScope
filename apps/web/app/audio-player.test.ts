import { describe, expect, it } from "vitest";
import { AudioContextPort, SynchronizedStemPlayer } from "./audio-player";

function fakeContext() {
  let now = 0;
  const sources: { startAt: number; offset: number; stopped: boolean; ended?: (() => void) | null }[] = [];
  const context = {
    get currentTime() { return now; },
    destination: {} as AudioNode,
    createGain: () => ({ gain: { value: 1 }, connect: () => undefined } as unknown as GainNode),
    createBufferSource: () => {
      const source = { startAt: 0, offset: 0, stopped: false };
      sources.push(source);
      return {
        buffer: undefined,
        connect: () => undefined,
        start: (at: number, offset: number) => { source.startAt = at; source.offset = offset; },
        stop: () => { source.stopped = true; },
        set onended(handler: (() => void) | null) { source.ended = handler; },
      } as unknown as AudioBufferSourceNode;
    },
    resume: async () => undefined,
    advance: (seconds: number) => { now += seconds; },
    sources,
  };
  return context;
}

function buffers() {
  return { vocals: { duration: 30 } as AudioBuffer, instrumental: { duration: 30 } as AudioBuffer };
}

describe("SynchronizedStemPlayer", () => {
  it("does not create playback sources before both buffers are ready", async () => {
    const context = fakeContext();
    const player = new SynchronizedStemPlayer(context as unknown as AudioContextPort);
    await player.play();
    expect(context.sources).toHaveLength(0);
  });

  it("starts both stems against the same clock and offset", async () => {
    const context = fakeContext();
    const player = new SynchronizedStemPlayer(context as unknown as AudioContextPort);
    player.setBuffers(buffers());
    await player.play();
    expect(context.sources).toHaveLength(2);
    expect(context.sources[0].startAt).toBe(context.sources[1].startAt);
    expect(context.sources[0].offset).toBe(context.sources[1].offset);
  });

  it("preserves a shared offset through pause and seek", async () => {
    const context = fakeContext();
    const player = new SynchronizedStemPlayer(context as unknown as AudioContextPort);
    player.setBuffers(buffers());
    await player.play();
    context.advance(4);
    player.pause();
    expect(player.currentTime).toBeCloseTo(3.95, 1);
    player.seek(12);
    expect(player.currentTime).toBe(12);
    player.setGain("vocals", 0.25);
    expect(player.currentTime).toBe(12);
    expect(context.sources).toHaveLength(2);
  });

  it("stops old sources when buffers are replaced", async () => {
    const context = fakeContext();
    const player = new SynchronizedStemPlayer(context as unknown as AudioContextPort);
    player.setBuffers(buffers());
    await player.play();
    const first = context.sources.slice();
    player.setBuffers(buffers());
    expect(player.isPlaying).toBe(false);
    expect(first.every((source) => source.stopped)).toBe(true);
  });

  it("resets after both stems end and can replay", async () => {
    const context = fakeContext();
    const player = new SynchronizedStemPlayer(context as unknown as AudioContextPort);
    player.setBuffers(buffers());
    await player.play();
    context.sources[0].ended?.();
    expect(player.isPlaying).toBe(true);
    context.sources[1].ended?.();
    expect(player.isPlaying).toBe(false);
    await player.play();
    expect(player.isPlaying).toBe(true);
  });
});
