import { render, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { useTelegram } from "./useTelegram";

const navigate = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => navigate,
}));

vi.mock("../lib/telegram-theme", () => ({
  __esModule: true,
  default: () => "light",
}));

describe("useTelegram start_param", () => {
  afterEach(() => {
    delete (window as any).Telegram;
    delete (window as any).tgWebAppStartParam;
    navigate.mockReset();
  });

  it("navigates to reminders when start_param is reminders", async () => {
    (window as any).Telegram = {
      WebApp: {
        initDataUnsafe: { user: { id: 1 }, start_param: "reminders" },
        initData: "",
        expand: vi.fn(),
        ready: vi.fn(),
        onEvent: vi.fn(),
        offEvent: vi.fn(),
      },
    };

    const TestComponent = () => {
      useTelegram();
      return null;
    };

    render(<TestComponent />);

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith("/reminders");
    });
  });

  it("navigates to reminders when tgWebAppStartParam is reminders", async () => {
    (window as any).Telegram = {
      WebApp: {
        initDataUnsafe: { user: { id: 1 } },
        initData: "",
        expand: vi.fn(),
        ready: vi.fn(),
        onEvent: vi.fn(),
        offEvent: vi.fn(),
      },
    };
    (window as any).tgWebAppStartParam = "reminders";

    const TestComponent = () => {
      useTelegram();
      return null;
    };

    render(<TestComponent />);

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith("/reminders");
    });
  });
});
