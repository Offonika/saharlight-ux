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
    const option = new Option()
    option.style.color = '#ff0000'
    expect(styleTag?.textContent).toContain(`--color-safe: ${option.style.color}`)
    expect(styleTag?.textContent).not.toContain('--color-unsafe')
    expect(styleTag?.textContent).not.toContain('javascript')
  })

  it('blocks style injections', () => {
    const config: ChartConfig = {
      safe: { color: '#00ff00' },
      inject: { color: "</style><script>window.xss=true</script>" },
    }

    const { container } = render(<ChartStyle id="test" config={config} />)
    const styleTag = container.querySelector('style')
    expect(styleTag?.textContent).toContain('--color-safe')
    expect(styleTag?.textContent).not.toContain('--color-inject')
    expect(container.querySelector('script')).toBeNull()
  })
})
