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

    const { unmount } = render(<ChartStyle id="test" config={config} />)
    const styleTag = document.head.querySelector(
      'style[data-chart-style="test"]'
    )
    const option = new Option()
    option.style.color = '#ff0000'
    expect(styleTag?.textContent).toContain(
      `--color-safe: ${option.style.color}`
    )
    expect(styleTag?.textContent).not.toContain('--color-unsafe')
    expect(styleTag?.textContent).not.toContain('javascript')
    unmount()
  })

  it('blocks style injections', () => {
    const config: ChartConfig = {
      safe: { color: '#00ff00' },
      inject: { color: "</style><script>window.xss=true</script>" },
    }

    const { unmount } = render(<ChartStyle id="test" config={config} />)
    const styleTag = document.head.querySelector(
      'style[data-chart-style="test"]'
    )
    expect(styleTag?.textContent).toContain('--color-safe')
    expect(styleTag?.textContent).not.toContain('--color-inject')
    expect(document.head.querySelector('script')).toBeNull()
    unmount()
  })
})
