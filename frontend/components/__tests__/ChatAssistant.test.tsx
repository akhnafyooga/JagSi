import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ChatAssistant } from '../ChatAssistant';

afterEach(() => {
  vi.unstubAllGlobals();
});

function ask(text: string) {
  fireEvent.change(screen.getByPlaceholderText('Tanyakan kondisi kesehatan…'), {
    target: { value: text },
  });
  fireEvent.click(screen.getByLabelText('Kirim'));
}

describe('ChatAssistant', () => {
  it('shows the answer from the backend', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ answer: 'Detak jantung stabil hari ini.', source: 'gemini', model: 'm' }),
      }),
    );
    render(<ChatAssistant />);
    ask('Bagaimana detak jantungnya?');
    expect(await screen.findByText('Detak jantung stabil hari ini.')).toBeInTheDocument();
    expect(screen.queryByText('Jawaban otomatis, bukan dari AI')).not.toBeInTheDocument();
  });

  it('labels a rule-based answer so it is not mistaken for AI', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ answer: 'Ringkasan data terakhir.', source: 'rules', model: 'JagSi rules' }),
      }),
    );
    render(<ChatAssistant />);
    ask('Halo');
    expect(await screen.findByText('Jawaban otomatis, bukan dari AI')).toBeInTheDocument();
  });

  it('says the server is unreachable instead of inventing an answer', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network')));
    render(<ChatAssistant />);
    ask('Halo');
    await waitFor(() => expect(screen.getByText(/server JagSi sedang tidak bisa dihubungi/)).toBeInTheDocument());
  });
});
