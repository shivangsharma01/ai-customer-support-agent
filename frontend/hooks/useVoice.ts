"use client";

import { useCallback, useRef, useState } from "react";
import { WS_URL } from "@/lib/api";

/** Streams mic audio (PCM16 @ 24kHz) to /ws/voice and plays the agent's audio replies.
 *  The backend relays OpenAI Realtime events; server VAD handles turn taking. */
export function useVoice(customerId: string, sessionId: string | null) {
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const ctx = useRef<AudioContext | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const playhead = useRef(0);

  const stop = useCallback(() => {
    ws.current?.close();
    ws.current = null;
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    ctx.current?.close();
    ctx.current = null;
    setActive(false);
  }, []);

  const playDelta = (b64: string) => {
    const audio = ctx.current;
    if (!audio) return;
    const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    const pcm = new Int16Array(bytes.buffer);
    const buf = audio.createBuffer(1, pcm.length, 24000);
    const ch = buf.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) ch[i] = pcm[i] / 32768;
    const src = audio.createBufferSource();
    src.buffer = buf;
    src.connect(audio.destination);
    playhead.current = Math.max(playhead.current, audio.currentTime);
    src.start(playhead.current);
    playhead.current += buf.duration;
  };

  const start = useCallback(async () => {
    setError(null);
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError("Microphone access denied.");
      return;
    }
    const audio = new AudioContext({ sampleRate: 24000 });
    ctx.current = audio;
    playhead.current = 0;

    const sid = sessionId ?? `voice-${Math.random().toString(36).slice(2, 10)}`;
    const sock = new WebSocket(
      `${WS_URL}/ws/voice?customer_id=${customerId}&session_id=${sid}`
    );
    ws.current = sock;

    sock.onmessage = (msg) => {
      const event = JSON.parse(msg.data);
      if (event.type === "error") {
        setError(event.message ?? event.error?.message ?? "Voice error.");
        stop();
      } else if (
        (event.type === "response.output_audio.delta" ||
          event.type === "response.audio.delta") &&
        event.delta
      ) {
        playDelta(event.delta);
      }
    };
    sock.onclose = () => setActive(false);

    sock.onopen = () => {
      const source = audio.createMediaStreamSource(stream.current!);
      const proc = audio.createScriptProcessor(4096, 1, 1);
      source.connect(proc);
      proc.connect(audio.destination);
      proc.onaudioprocess = (e) => {
        if (sock.readyState !== WebSocket.OPEN) return;
        const f32 = e.inputBuffer.getChannelData(0);
        const pcm = new Int16Array(f32.length);
        for (let i = 0; i < f32.length; i++) {
          pcm[i] = Math.max(-32768, Math.min(32767, f32[i] * 32768));
        }
        const b64 = btoa(
          String.fromCharCode(...new Uint8Array(pcm.buffer))
        );
        sock.send(JSON.stringify({ type: "input_audio_buffer.append", audio: b64 }));
      };
      setActive(true);
    };
  }, [customerId, sessionId, stop]);

  return { active, error, start, stop };
}
