import { describe, expect, it } from 'vitest';
import {
  classifyHeartRate,
  classifySpO2,
  classifyTemperature,
  cn,
} from '../utils';

describe('cn', () => {
  it('joins truthy class names and drops falsy ones', () => {
    expect(cn('a', false, 'b', null, undefined, 'c')).toBe('a b c');
  });

  it('returns empty string for no classes', () => {
    expect(cn()).toBe('');
  });
});

describe('classifyHeartRate', () => {
  it('is normal within 60–100 bpm', () => {
    expect(classifyHeartRate(78)).toBe('normal');
  });

  it('is warning at the low boundary', () => {
    expect(classifyHeartRate(55)).toBe('warning');
  });

  it('is critical when very low', () => {
    expect(classifyHeartRate(45)).toBe('critical');
  });
});

describe('classifySpO2', () => {
  it('is normal at 98%', () => {
    expect(classifySpO2(98)).toBe('normal');
  });

  it('is critical below 90%', () => {
    expect(classifySpO2(88)).toBe('critical');
  });
});

describe('classifyTemperature', () => {
  it('is normal at 36.5°C', () => {
    expect(classifyTemperature(36.5)).toBe('normal');
  });

  it('is warning at 37.8°C', () => {
    expect(classifyTemperature(37.8)).toBe('warning');
  });
});
