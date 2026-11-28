'use client';

import { useState } from 'react';
import { Icon } from './Icon';

const topics = [
  { question: 'Bagaimana membaca ringkasan AI?', answer: 'Buka Ringkasan AI di Beranda. JagSi membandingkan 60 pembacaan terakhir. Jika jumlahnya belum cukup, kartu menampilkan kemajuan pengumpulan data.' },
  { question: 'Di mana saya melihat tren harian?', answer: 'Buka Riwayat untuk melihat tren detak jantung dan saturasi oksigen selama periode yang tersedia.' },
  { question: 'Di mana saya memeriksa peringatan?', answer: 'Buka Darurat untuk melihat peringatan jatuh dan SOS yang diterima dari jam tangan.' },
];

export function ChatAssistant() {
  const [selected, setSelected] = useState<number | null>(null);
  return (
    <section className="ungu-panel ungu-assistant">
      <h2 className="ungu-panel-title"><Icon name="forum" />Asisten JagSi</h2>
      <p className="text-sm text-on-surface-variant">Demo percakapan · Pilih pertanyaan untuk melihat jawaban contoh.</p>
      <div className="ungu-topic-list">
        {topics.map((topic, index) => (
          <button key={topic.question} type="button" aria-pressed={selected === index}
            className="ungu-topic"
            onClick={() => setSelected(index)}>
            <span>{topic.question}</span><Icon name="arrow_forward" />
          </button>
        ))}
      </div>
      <div aria-live="polite">
        {selected !== null && <p className="rounded-xl bg-primary-container p-4 text-sm">{topics[selected].answer}</p>}
      </div>
    </section>
  );
}
