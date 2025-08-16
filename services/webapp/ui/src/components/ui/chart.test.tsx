import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ChartConfig } from './chart'
import { ChartStyle } from './chart'

describe('ChartStyle', () => {
  it('ignores invalid color strings', () => {
    const config: ChartConfig = {
      safe: { color: '#ff0000' },
      unsafe: { color: "red; background: url(javascript:alert('xss'))" },
    }

    const { container } = render(<ChartStyle id="test" config={config} />)
    const styleTag = container.querySelector('style')
    expect(styleTag?.innerHTML).toContain('--color-safe: #ff0000')
    expect(styleTag?.innerHTML).not.toContain('--color-unsafe')
    expect(styleTag?.innerHTML).not.toContain('javascript')
  })
})
