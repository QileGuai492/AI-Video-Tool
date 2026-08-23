import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import client from "../api/client";
import Settings from "../pages/Settings";

vi.mock("../api/client", () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

const mockedGet = vi.mocked(client.get);
const mockedPut = vi.mocked(client.put);

describe("Settings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("加载时读取用户设置", async () => {
    mockedGet.mockResolvedValue({
      data: {
        default_aspect_ratio: "9:16",
        default_quality: "high",
        default_model: "agnes-video-v2.0",
        cost_limit: 80,
      },
    });

    render(<Settings />);

    await waitFor(() => expect(mockedGet).toHaveBeenCalledWith("/settings"));
    expect(screen.getByRole("button", { name: "保存设置" })).toBeInTheDocument();
  });

  it("点击保存会提交设置", async () => {
    const user = userEvent.setup();
    mockedGet.mockResolvedValue({ data: {} });
    mockedPut.mockResolvedValue({});

    render(<Settings />);
    await waitFor(() => expect(mockedGet).toHaveBeenCalledWith("/settings"));
    await user.click(screen.getByRole("button", { name: "保存设置" }));

    expect(mockedPut).toHaveBeenCalledWith("/settings", expect.any(Object));
  });

  it("可以修改用户名并提交", async () => {
    const user = userEvent.setup();
    mockedGet.mockImplementation((url: string) => {
      if (url === "/auth/me") {
        return Promise.resolve({
          data: {
            id: 1,
            uid: "user-uid",
            username: "old_name",
            email: "",
            created_at: "2026-01-01T00:00:00Z",
          },
        });
      }
      return Promise.resolve({ data: {} });
    });
    mockedPut.mockResolvedValue({});

    render(<Settings />);
    await waitFor(() => expect(mockedGet).toHaveBeenCalledWith("/auth/me"));

    const usernameInput = screen.getByDisplayValue("old_name");
    await user.clear(usernameInput);
    await user.type(usernameInput, "new_name");
    await user.click(screen.getByRole("button", { name: "保存用户信息" }));

    expect(mockedPut).toHaveBeenCalledWith(
      "/auth/me",
      expect.objectContaining({ username: "new_name" })
    );
  });
});
