import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { ChatAssistant } from '../ChatAssistant';

it('offers only preset topics and switches to the selected answer', () => {
  render(<ChatAssistant />);
  expect(screen.queryByRole('textbox')).toBeNull();
  expect(screen.getAllByRole('button')).toHaveLength(3);
  fireEvent.click(screen.getByRole('button', { name: /ringkasan AI/i }));
  expect(screen.getByText(/membandingkan 60/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /peringatan/i }));
  expect(screen.getByText(/Buka Darurat/)).toBeInTheDocument();
  expect(screen.queryByText(/membandingkan 60/)).toBeNull();
});
