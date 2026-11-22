import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Icon } from '../Icon';

describe('Icon', () => {
  it('applies a text-[..px] size inline so the Google icon stylesheet cannot override it', () => {
    const { container } = render(<Icon name="sos" className="text-[40px] text-error" />);
    expect((container.firstChild as HTMLElement).style.fontSize).toBe('40px');
  });

  it('leaves the size alone when none is given', () => {
    const { container } = render(<Icon name="home" className="text-primary" />);
    expect((container.firstChild as HTMLElement).style.fontSize).toBe('');
  });
});
