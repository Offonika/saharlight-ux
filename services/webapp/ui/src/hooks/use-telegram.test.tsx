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
  const win = window as Record<string, unknown>;

  afterEach(() => {
    delete win.Telegram;
    delete win.tgWebAppStartParam;
    window.history.pushState({}, "", "/");
    navigate.mockReset();
  });

  it("navigates to reminders when start_param is reminders", async () => {
    win.Telegram = {
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
    win.Telegram = {
      WebApp: {
        initDataUnsafe: { user: { id: 1 } },
        initData: "",
        expand: vi.fn(),
        ready: vi.fn(),
        onEvent: vi.fn(),
        offEvent: vi.fn(),
      },
    };
    win.tgWebAppStartParam = "reminders";

    const TestComponent = () => {
      useTelegram();
      return null;
    };

    render(<TestComponent />);

    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith("/reminders");
    });
  });

  it("navigates to reminders when query param tgWebAppStartParam is reminders", async () => {
    win.Telegram = {
      WebApp: {
        initDataUnsafe: { user: { id: 1 } },
        initData: "",
        expand: vi.fn(),
        ready: vi.fn(),
        onEvent: vi.fn(),
        offEvent: vi.fn(),
      },
    };

    const url = new URL(window.location.href);
    url.search = "?tgWebAppStartParam=reminders";
    window.history.pushState({}, "", url);

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
