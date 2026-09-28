'use client';

import { useState } from 'react';
import { Icon } from './Icon';

interface Message {
  role: 'assistant' | 'user';
  text: string;
}

const initialMessages: Message[] = [
  {
    role: 'assistant',
    text: 'Halo, saya asisten kesehatan JagSi. Tanyakan apa pun tentang kondisi Ibu Sari.',
  },
];

export function ChatAssistant() {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState('');

  function submit() {
    const text = input.trim();
    if (!text) return;
    setMessages((prev) => [
      ...prev,
      { role: 'user', text },
      {
        role: 'assistant',
        text: 'Baik, saya akan bantu analisis. (Demo — terhubung ke JagSi AI pada Sprint 5.)',
      },
    ]);
    setInput('');
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
        <div className="space-y-2">
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
              </div>
            </div>
          ))}
        </div>

        <div className="mt-3 flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submit()}
            placeholder="Tanyakan kondisi kesehatan…"
            className="min-w-0 flex-1 rounded-xl border border-outline-variant/40 bg-surface-container-low px-3 py-2.5 text-sm outline-none focus:border-primary"
          />
          <button
            onClick={submit}
            aria-label="Kirim"
            type="button"
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-on-primary transition-colors hover:bg-primary-dim active:scale-95"
          >
            <Icon name="send" className="text-[18px]" />
          </button>
        </div>
      </div>
    </section>
  );
}
