import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { VitalCard } from '../VitalCard';
import type { Vital } from '@/lib/types';

const vital: Vital = {
  id: 'heart-rate',
  label: 'Detak Jantung',
  value: 78,
  unit: 'bpm',
  icon: 'favorite',
  tone: 'normal',
  statusLabel: 'Normal',
  note: 'Rentang normal 60–100 bpm',
};

describe('VitalCard', () => {
  it('renders the label, value and status', () => {
    render(<VitalCard vital={vital} />);
    expect(screen.getByText('Detak Jantung')).toBeInTheDocument();
    expect(screen.getByText('78')).toBeInTheDocument();
    expect(screen.getByText('bpm')).toBeInTheDocument();
    expect(screen.getByText('Normal')).toBeInTheDocument();
  });
});
