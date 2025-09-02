import { render } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { ChartStyle, ChartConfig } from "./chart"

describe("ChartStyle color validation", () => {
  const id = "test"

  it("ignores invalid color values", () => {
    const config: ChartConfig = {
      series: { color: "javascript:alert(1)" },
    }
    const { container } = render(<ChartStyle id={id} config={config} />)
    const style = container.querySelector("style")
    expect(style?.innerHTML).not.toContain("--color-series")
  })

  it("applies valid color values", () => {
    const config: ChartConfig = {
      series: { color: "#abc" },
    }
    const { container } = render(<ChartStyle id={id} config={config} />)
    const style = container.querySelector("style")
    expect(style?.innerHTML).toContain("--color-series: #abc")
  })
})
