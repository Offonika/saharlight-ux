import { describe, it, expect } from 'vitest';
import { parseProfile } from '../src/pages/Profile';

describe('parseProfile', () => {
  it('returns parsed numbers for valid input', () => {
    const result = parseProfile({ icr: '1', cf: '2', target: '3', low: '4', high: '5' });
    expect(result).toEqual({ icr: 1, cf: 2, target: 3, low: 4, high: 5 });
  });

  it('returns null when any value is non-positive or invalid', () => {
    expect(parseProfile({ icr: '0', cf: '2', target: '3', low: '4', high: '5' })).toBeNull();
    expect(parseProfile({ icr: '1', cf: '-1', target: '3', low: '4', high: '5' })).toBeNull();
    expect(parseProfile({ icr: 'a', cf: '2', target: '3', low: '4', high: '5' })).toBeNull();
  });
});
