import React from "react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, fireEvent, cleanup } from "@testing-library/react";
import AfterEventDelay from "../src/features/reminders/components/AfterEventDelay";

const renderWithState = (initial?: number) => {
  const Wrapper: React.FC = () => {
    const [value, setValue] = React.useState<number | undefined>(initial);
    return <AfterEventDelay value={value} onChange={setValue} />;
  };
  return render(<Wrapper />);
};

afterEach(() => cleanup());

describe("AfterEventDelay", () => {
  it("renders number input with constraints", () => {
    const { getByLabelText } = render(
      <AfterEventDelay value={60} onChange={() => {}} />
    );
    const input = getByLabelText(
      "Задержка после еды (мин)"
    ) as HTMLInputElement;
    expect(input).toBeTruthy();
    expect(input.min).toBe("5");
    expect(input.max).toBe("480");
    expect(input.step).toBe("5");
  });

  it("activates preset and updates value on click", () => {
    const onChange = vi.fn();
    const { getByRole } = render(
      <AfterEventDelay value={60} onChange={onChange} />
    );
    const preset90 = getByRole("button", { name: "90" });
    fireEvent.click(preset90);
    expect(onChange).toHaveBeenCalledWith(90);
  });

  it("deactivates preset when manual input differs", () => {
    const { getByLabelText, getByRole } = renderWithState(60);
    const input = getByLabelText("Задержка после еды (мин)") as HTMLInputElement;
    const preset60 = getByRole("button", { name: "60" });
    expect(preset60.getAttribute("aria-pressed")).toBe("true");
    fireEvent.change(input, { target: { value: "65" } });
    expect(preset60.getAttribute("aria-pressed")).toBe("false");
  });
});

