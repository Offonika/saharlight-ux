import { render, waitFor, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useLocation: () => ({ state: undefined }),
  useParams: () => ({ id: "1" }),
}));

vi.mock("../contexts/telegram-context", () => ({
  useTelegramContext: () => ({ user: { id: 123 }, sendData: vi.fn() }),
}));

vi.mock("../api/reminders", () => ({
  getReminder: vi.fn().mockResolvedValue({
    id: 1,
    type: "sugar",
    time: "08:00",
    title: "Test",
    intervalHours: 1,
  }),
  createReminder: vi.fn(),
  updateReminder: vi.fn(),
}));

import CreateReminder from "./CreateReminder";
import { getReminder, updateReminder } from "../api/reminders";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("CreateReminder", () => {
  it("requests reminder only once", async () => {
    render(<CreateReminder />);
    await waitFor(() => expect(getReminder).toHaveBeenCalledTimes(1));
    const [, , signal] = vi.mocked(getReminder).mock.calls[0];
    expect(signal).toBeInstanceOf(AbortSignal);
  });

  it("submits custom title", async () => {
    render(<CreateReminder />);
    await waitFor(() => expect(getReminder).toHaveBeenCalled());
    const input = screen.getByLabelText("Название");
    fireEvent.change(input, { target: { value: "Custom" } });
    fireEvent.click(screen.getAllByText("Сохранить")[0]);
    await waitFor(() => expect(updateReminder).toHaveBeenCalled());
    expect(updateReminder).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Custom" }),
    );
  });
});
