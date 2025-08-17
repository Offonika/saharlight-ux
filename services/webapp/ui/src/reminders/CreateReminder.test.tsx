import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
  useLocation: () => ({ state: undefined }),
  useParams: () => ({ id: "1" }),
}));

vi.mock("@/contexts/telegram-context", () => ({
  useTelegramContext: () => ({ user: { id: 123 }, sendData: vi.fn() }),
}));

vi.mock("@/api/reminders", () => ({
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
import { getReminder } from "@/api/reminders";

describe("CreateReminder", () => {
  it("requests reminder only once", async () => {
    render(<CreateReminder />);
    await waitFor(() => expect(getReminder).toHaveBeenCalledTimes(1));
  });
});
