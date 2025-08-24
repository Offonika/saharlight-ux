import { render, waitFor, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const mockNavigate = vi.fn();
const mockUseParams = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
  useLocation: () => ({ state: undefined }),
  useParams: () => mockUseParams(),
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
import { getReminder, createReminder } from "../api/reminders";

describe("CreateReminder", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  afterEach(() => {
    cleanup();
  });

  it("requests reminder only once", async () => {
    mockUseParams.mockReturnValue({ id: "1" });
    render(<CreateReminder />);
    await waitFor(() => expect(getReminder).toHaveBeenCalledTimes(1));
    const [, , signal] = vi.mocked(getReminder).mock.calls[0];
    expect(signal).toBeInstanceOf(AbortSignal);
  });

  it("sends title when saving", async () => {
    mockUseParams.mockReturnValue({});
    vi.mocked(createReminder).mockResolvedValue({ id: 1 });
    render(<CreateReminder />);

    fireEvent.change(screen.getByLabelText("Название"), {
      target: { value: "My title" },
    });
    fireEvent.change(screen.getByLabelText("Время"), {
      target: { value: "08:00" },
    });
    fireEvent.change(screen.getByLabelText("Интервал (мин)"), {
      target: { value: "60" },
    });
    fireEvent.click(screen.getByText("Сохранить"));

    await waitFor(() => expect(createReminder).toHaveBeenCalled());
    expect(vi.mocked(createReminder).mock.calls[0][0]).toMatchObject({
      title: "My title",
    });
  });
});
