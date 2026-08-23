import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import client from "../api/client";
import Tasks from "../pages/Tasks";

vi.mock("../api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const mockedGet = vi.mocked(client.get);
const mockedPost = vi.mocked(client.post);

describe("Tasks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("根据状态显示取消/重试/下载按钮", async () => {
    mockedGet.mockResolvedValue({
      data: [
        { id: 1, prompt: "进行中", status: "pending", video_url: null, created_at: "2026-01-01T00:00:00Z" },
        { id: 2, prompt: "失败", status: "failed", video_url: null, created_at: "2026-01-01T00:00:00Z" },
        { id: 3, prompt: "完成", status: "completed", video_url: "/uploads/v.mp4", created_at: "2026-01-01T00:00:00Z" },
      ],
    });

    render(<Tasks />);

    await waitFor(() => expect(screen.getByText("任务 #1")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /取\s*消/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /重\s*试/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /下\s*载/ })).toBeInTheDocument();
  });

  it("点击取消会调用 cancel 接口", async () => {
    const user = userEvent.setup();
    mockedGet.mockResolvedValue({
      data: [{ id: 1, prompt: "进行中", status: "pending", video_url: null, created_at: "2026-01-01T00:00:00Z" }],
    });
    mockedPost.mockResolvedValue({});

    render(<Tasks />);
    await screen.findByText("任务 #1");
    await user.click(screen.getByRole("button", { name: /取\s*消/ }));

    expect(mockedPost).toHaveBeenCalledWith("/generate/1/cancel");
  });

  it("点击重试会调用 retry 接口", async () => {
    const user = userEvent.setup();
    mockedGet.mockResolvedValue({
      data: [{ id: 2, prompt: "失败", status: "failed", video_url: null, created_at: "2026-01-01T00:00:00Z" }],
    });
    mockedPost.mockResolvedValue({});

    render(<Tasks />);
    await screen.findByText("任务 #2");
    await user.click(screen.getByRole("button", { name: /重\s*试/ }));

    expect(mockedPost).toHaveBeenCalledWith("/generate/2/retry");
  });
});
