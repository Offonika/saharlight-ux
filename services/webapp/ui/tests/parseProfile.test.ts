import { describe, it, expect } from 'vitest';
import { parseProfile } from '../src/pages/Profile';

describe('parseProfile', () => {
  it('returns parsed numbers for valid input', () => {
    const result = parseProfile({
      icr: '1',
      cf: '2',
      target: '5',
      low: '4',
      high: '10',
    });
    expect(result).toEqual({ icr: 1, cf: 2, target: 5, low: 4, high: 10 });
  });

  it('handles comma as decimal separator', () => {
    const result = parseProfile({
      icr: '1,5',
      cf: '2,5',
      target: '5,5',
      low: '4,4',
      high: '10,1',
    });
    expect(result).toEqual({
      icr: 1.5,
      cf: 2.5,
      target: 5.5,
      low: 4.4,
      high: 10.1,
    });
  });

  it('returns null when any value is non-positive or invalid', () => {
    expect(
      parseProfile({ icr: '0', cf: '2', target: '5', low: '4', high: '10' }),
    ).toBeNull();
    expect(
      parseProfile({ icr: '1', cf: '-1', target: '5', low: '4', high: '10' }),
    ).toBeNull();
    expect(
      parseProfile({ icr: 'a', cf: '2', target: '5', low: '4', high: '10' }),
    ).toBeNull();
  });

  it('returns null when low/high bounds are invalid', () => {
    expect(
      parseProfile({ icr: '1', cf: '2', target: '5', low: '8', high: '6' }),
    ).toBeNull();
    expect(
      parseProfile({ icr: '1', cf: '2', target: '3', low: '4', high: '10' }),
    ).toBeNull();
    expect(
      parseProfile({ icr: '1', cf: '2', target: '12', low: '4', high: '10' }),
    ).toBeNull();
  });
});
