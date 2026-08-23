import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import client from "../api/client";
import Templates from "../pages/Templates";

vi.mock("../api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockedGet = vi.mocked(client.get);
const mockedPost = vi.mocked(client.post);
const mockedDelete = vi.mocked(client.delete);

describe("Templates", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("加载模板列表并显示内置/我的标签", async () => {
    mockedGet.mockResolvedValue({
      data: [
        { id: 1, name: "内置模板", config_json: {}, is_builtin: true, created_at: "2026-01-01T00:00:00Z" },
        { id: 2, name: "我的模板", config_json: {}, is_builtin: false, created_at: "2026-01-01T00:00:00Z" },
      ],
    });

    render(<Templates />);

    await waitFor(() => expect(screen.getByText("内置模板")).toBeInTheDocument());
    expect(screen.getByText("我的模板")).toBeInTheDocument();
  });

  it("复制模板会调用 POST /templates/{id}/fork", async () => {
    const user = userEvent.setup();
    mockedGet.mockResolvedValue({
      data: [{ id: 1, name: "内置模板", config_json: {}, is_builtin: true, created_at: "2026-01-01T00:00:00Z" }],
    });
    mockedPost.mockResolvedValue({});

    render(<Templates />);
    await screen.findByText("内置模板");
    await user.click(screen.getByRole("button", { name: /复\s*制/ }));

    expect(mockedPost).toHaveBeenCalledWith("/templates/1/fork");
  });

  it("删除自己的模板会调用 DELETE /templates/{id}", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    mockedGet.mockResolvedValue({
      data: [{ id: 2, name: "我的模板", config_json: {}, is_builtin: false, created_at: "2026-01-01T00:00:00Z" }],
    });
    mockedDelete.mockResolvedValue({});

    render(<Templates />);
    await screen.findByText("我的模板");
    await user.click(screen.getByRole("button", { name: /删\s*除/ }));

    expect(mockedDelete).toHaveBeenCalledWith("/templates/2");
    confirmSpy.mockRestore();
  });
});
