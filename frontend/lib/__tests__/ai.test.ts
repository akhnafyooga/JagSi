import { afterEach, describe, expect, it, vi } from 'vitest';

import { askAssistant, fetchSummary, summarySourceLabel } from '../api';

function mockFetch(body: unknown, ok = true, status = 200) {
  const fn = vi.fn().mockResolvedValue({ ok, status, json: async () => body });
  vi.stubGlobal('fetch', fn);
  return fn;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('summarySourceLabel', () => {
  it('names the Gemini model when the model answered', () => {
    expect(summarySourceLabel('gemini', 'gemini-3.8-flash')).toBe('Gemini · gemini-3.8-flash');
  });

  it('never presents the rule-based fallback or demo text as AI', () => {
    expect(summarySourceLabel('rules', 'JagSi rules')).toBe('Ringkasan otomatis');
    expect(summarySourceLabel('demo', '')).toBe('Data demo');
  });
});

describe('fetchSummary', () => {
  it('asks for a fresh summary only when told to', async () => {
    const fn = mockFetch({ text: 'ok' });
    await fetchSummary();
    await fetchSummary(true);
    expect(fn.mock.calls[0][0]).toMatch(/\/api\/devices\/jagsi-watch-01\/summary$/);
    expect(fn.mock.calls[1][0]).toMatch(/summary\?refresh=true$/);
  });

  it('throws on a server error so the card can fall back', async () => {
    mockFetch({}, false, 500);
    await expect(fetchSummary()).rejects.toThrow('500');
  });
});

describe('askAssistant', () => {
  it('posts the question with at most six turns of history', async () => {
    const fn = mockFetch({ answer: 'Stabil.', source: 'gemini', model: 'm' });
    const history = Array.from({ length: 10 }, (_, i) => ({
      role: (i % 2 ? 'assistant' : 'user') as 'user' | 'assistant',
      text: `t${i}`,
    }));
    const reply = await askAssistant('Bagaimana kondisinya?', history);
    expect(reply.answer).toBe('Stabil.');
    const [url, init] = fn.mock.calls[0];
    expect(url).toMatch(/\/chat$/);
    expect(init.method).toBe('POST');
    const sent = JSON.parse(init.body);
    expect(sent.question).toBe('Bagaimana kondisinya?');
    expect(sent.history).toHaveLength(6);
    expect(sent.history[5].text).toBe('t9');
  });

  it('throws when the backend refuses', async () => {
    mockFetch({ detail: 'x' }, false, 400);
    await expect(askAssistant('')).rejects.toThrow('400');
  });
});
