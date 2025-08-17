import { describe, it, expect } from 'vitest'
import { parseTimeToMinutes, isValidTime, isValidTimeFormat } from './time'

describe('parseTimeToMinutes', () => {
  it('parses valid times', () => {
    expect(parseTimeToMinutes('00:00')).toBe(0)
    expect(parseTimeToMinutes('1:00')).toBe(60)
    expect(parseTimeToMinutes('23:59')).toBe(23 * 60 + 59)
  })

  it('returns NaN for invalid format', () => {
    expect(Number.isNaN(parseTimeToMinutes('abc'))).toBe(true)
    expect(Number.isNaN(parseTimeToMinutes('12-34'))).toBe(true)
    expect(Number.isNaN(parseTimeToMinutes('1234'))).toBe(true)
  })

  it('returns NaN for out-of-range values', () => {
    expect(Number.isNaN(parseTimeToMinutes('24:00'))).toBe(true)
    expect(Number.isNaN(parseTimeToMinutes('23:60'))).toBe(true)
    expect(Number.isNaN(parseTimeToMinutes('-1:00'))).toBe(true)
  })
})

describe('validation helpers', () => {
  it('validates proper times', () => {
    expect(isValidTime('00:00')).toBe(true)
    expect(isValidTime('23:59')).toBe(true)
  })

  it('detects invalid formats', () => {
    expect(isValidTimeFormat('abc')).toBe(false)
    expect(isValidTime('abc')).toBe(false)
  })

  it('detects out-of-range times', () => {
    expect(isValidTime('24:00')).toBe(false)
    expect(isValidTime('23:60')).toBe(false)
  })
})
