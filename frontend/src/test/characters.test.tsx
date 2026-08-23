import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import client from "../api/client";
import Characters from "../pages/Characters";

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

describe("Characters", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("加载角色列表并显示角色名称", async () => {
    mockedGet.mockResolvedValue({
      data: [
        {
          id: 1,
          name: "测试角色",
          reference_image_url: "https://example.com/a.png",
          description: "描述",
          created_at: "2026-01-01T00:00:00Z",
        },
      ],
    });

    render(<Characters />);

    await waitFor(() => expect(screen.getByText("测试角色")).toBeInTheDocument());
    expect(mockedGet).toHaveBeenCalledWith("/characters");
  });

  it("创建角色会调用 POST /characters", async () => {
    const user = userEvent.setup();
    mockedGet.mockResolvedValue({ data: [] });
    mockedPost.mockResolvedValue({});

    render(<Characters />);
    await waitFor(() => expect(mockedGet).toHaveBeenCalledWith("/characters"));

    await user.type(screen.getByPlaceholderText("角色名称"), "新角色");
    await user.type(screen.getByPlaceholderText("参考图 URL（可留空）"), "https://example.com/b.png");
    await user.click(screen.getByRole("button", { name: /创\s*建/ }));

    expect(mockedPost).toHaveBeenCalledWith(
      "/characters",
      expect.objectContaining({
        name: "新角色",
        reference_image_url: "https://example.com/b.png",
      })
    );
  });

  it("角色库提供图片上传入口", async () => {
    mockedGet.mockResolvedValue({ data: [] });

    render(<Characters />);

    await waitFor(() => expect(mockedGet).toHaveBeenCalledWith("/characters"));
    expect(screen.getByRole("button", { name: /上\s*传\s*图\s*片/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /上\s*传/ })).toBeInTheDocument();
  });

  it("删除角色会调用 DELETE /characters/{id}", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    mockedGet.mockResolvedValue({
      data: [
        {
          id: 1,
          name: "测试角色",
          reference_image_url: "https://example.com/a.png",
          description: "描述",
          created_at: "2026-01-01T00:00:00Z",
        },
      ],
    });
    mockedDelete.mockResolvedValue({});

    render(<Characters />);
    await screen.findByText("测试角色");
    await user.click(screen.getByRole("button", { name: /删\s*除/ }));

    expect(mockedDelete).toHaveBeenCalledWith("/characters/1");
    confirmSpy.mockRestore();
  });
});
