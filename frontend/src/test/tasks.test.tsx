import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import client from "../api/client";
import Tasks from "../pages/Tasks";

vi.mock("../api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockedGet = vi.mocked(client.get);
const mockedDelete = vi.mocked(client.delete);

describe("Tasks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("任务卡片显示下载和删除按钮", async () => {
    mockedGet.mockResolvedValue({
      data: [
        { id: 1, uid: "task-uid-1", prompt: "进行中", status: "pending", video_url: null, created_at: "2026-01-01T00:00:00Z" },
        { id: 2, uid: "task-uid-2", prompt: "失败", status: "failed", video_url: null, created_at: "2026-01-01T00:00:00Z" },
        { id: 3, uid: "task-uid-3", prompt: "完成", status: "completed", video_url: "/uploads/v.mp4", created_at: "2026-01-01T00:00:00Z" },
      ],
    });

    render(<Tasks />);

    await waitFor(() => expect(screen.getByText("任务 #1")).toBeInTheDocument());
    expect(screen.getAllByRole("button", { name: /下\s*载/ }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: /删\s*除/ }).length).toBeGreaterThan(0);
  });

  it("任务中心显示状态筛选标签", async () => {
    mockedGet.mockResolvedValue({ data: [] });

    render(<Tasks />);

    await waitFor(() => expect(screen.getByText(/全\s*部/)).toBeInTheDocument());
    expect(screen.getByText(/进\s*行\s*中/)).toBeInTheDocument();
    expect(screen.getByText(/已\s*完\s*成/)).toBeInTheDocument();
    expect(screen.getByText(/失\s*败/)).toBeInTheDocument();
    expect(screen.getByText(/已\s*取\s*消/)).toBeInTheDocument();
  });

  it("点击删除会调用 delete 接口", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    mockedGet.mockResolvedValue({
      data: [{ id: 1, uid: "task-uid-1", prompt: "进行中", status: "pending", video_url: null, created_at: "2026-01-01T00:00:00Z" }],
    });
    mockedDelete.mockResolvedValue({});

    render(<Tasks />);
    await screen.findByText("任务 #1");
    await user.click(screen.getByRole("button", { name: /删\s*除/ }));

    expect(mockedDelete).toHaveBeenCalledWith("/generate/task-uid-1");
    confirmSpy.mockRestore();
  });

  it("点击下载会调用 download 接口", async () => {
    const user = userEvent.setup();
    mockedGet.mockResolvedValue({
      data: [{ id: 3, uid: "task-uid-3", prompt: "完成", status: "completed", video_url: "/uploads/v.mp4", created_at: "2026-01-01T00:00:00Z" }],
    });

    render(<Tasks />);
    await screen.findByText("任务 #3");
    await user.click(screen.getByRole("button", { name: /下\s*载/ }));

    expect(mockedGet).toHaveBeenCalledWith("/generate/task-uid-3/download", { responseType: "blob" });
  });
});
