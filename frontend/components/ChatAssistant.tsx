'use client';

import { useRef, useState } from 'react';

import { type ChatTurn, askAssistant } from '@/lib/api';
import { elder } from '@/lib/mock-data';

import { Icon } from './Icon';

interface Message extends ChatTurn {
  /** Marks answers from the backend's rule-based fallback, not from Gemini. */
  fallback?: boolean;
}

const greeting: Message = {
  role: 'assistant',
  text: `Halo, saya asisten kesehatan JagSi. Tanyakan apa pun tentang kondisi ${elder.name}.`,
};

const OFFLINE_ANSWER =
  'Maaf, server JagSi sedang tidak bisa dihubungi. Coba lagi sebentar lagi. Jika darurat, hubungi 112 atau 119.';

/**
 * Caregiver chat (issue #10). Questions go to POST /api/devices/{id}/chat, which
 * answers from the stored telemetry using Gemini, or with a rule-based summary
 * when no model is available. The greeting is not sent as history.
 */
export function ChatAssistant() {
  const [messages, setMessages] = useState<Message[]>([greeting]);
  const [input, setInput] = useState('');
  const [pending, setPending] = useState(false);
  const listEnd = useRef<HTMLDivElement>(null);

  async function submit() {
    const text = input.trim();
    if (!text || pending) return;
    const history: ChatTurn[] = messages.slice(1).map(({ role, text: t }) => ({ role, text: t }));
    setMessages((prev) => [...prev, { role: 'user', text }]);
    setInput('');
    setPending(true);
    try {
      const reply = await askAssistant(text, history);
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: reply.answer, fallback: reply.source !== 'gemini' },
      ]);
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', text: OFFLINE_ANSWER, fallback: true }]);
    } finally {
      setPending(false);
      requestAnimationFrame(() => listEnd.current?.scrollIntoView?.({ block: 'nearest' }));
    }
  }

  return (
    <section className="space-y-2.5">
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-on-primary">
          <Icon name="smart_toy" className="text-[16px]" />
        </div>
        <h2 className="text-base font-semibold tracking-tight text-on-surface">Tanya AI Kesehatan</h2>
      </div>

      <div className="rounded-2xl border border-surface-container-highest/60 bg-surface-container-lowest p-3 shadow-sm">
        <div className="space-y-2" aria-live="polite">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                  m.role === 'user'
                    ? 'bg-primary text-on-primary'
                    : 'bg-surface-container text-on-surface'
                }`}
              >
                {m.text}
                {m.fallback && (
                  <span className="mt-1 block text-[11px] text-on-surface-variant">
                    Jawaban otomatis, bukan dari AI
                  </span>
                )}
              </div>
            </div>
          ))}
          {pending && (
            <div className="flex justify-start">
              <div className="rounded-xl bg-surface-container px-3 py-2 text-sm text-on-surface-variant">
                Sedang menjawab…
              </div>
            </div>
          )}
          <div ref={listEnd} />
        </div>

        <p className="mt-2 text-[11px] text-on-surface-variant">
          Informasi umum dari data jam tangan, bukan diagnosis medis.
        </p>

        <div className="mt-2 flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && void submit()}
            placeholder="Tanyakan kondisi kesehatan…"
            maxLength={500}
            disabled={pending}
            className="min-w-0 flex-1 rounded-xl border border-outline-variant/40 bg-surface-container-low px-3 py-2.5 text-sm outline-none focus:border-primary disabled:opacity-60"
          />
          <button
            onClick={() => void submit()}
            aria-label="Kirim"
            type="button"
            disabled={pending || !input.trim()}
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-on-primary transition-colors hover:bg-primary-dim active:scale-95 disabled:opacity-50"
          >
            <Icon name="send" className="text-[18px]" />
          </button>
        </div>
      </div>
    </section>
  );
}
