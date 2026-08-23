import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import client from "../api/client";
import Workbench from "../pages/Workbench";

vi.mock("../api/client", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("../components/PrevisCanvas", () => ({
  default: () => <div data-testid="previs-canvas" />,
}));
vi.mock("../components/EditorToolbar", () => ({
  default: () => <div data-testid="editor-toolbar" />,
}));
vi.mock("../components/Timeline", () => ({
  default: () => <div data-testid="timeline" />,
}));
vi.mock("../components/ObjectProperties", () => ({
  default: () => <div data-testid="object-properties" />,
}));
vi.mock("../components/KeyframeList", () => ({
  default: () => <div data-testid="keyframe-list" />,
}));

const mockedGet = vi.mocked(client.get);
const mockedPost = vi.mocked(client.post);
const mockedPut = vi.mocked(client.put);
const mockedDelete = vi.mocked(client.delete);

const project = {
  id: 1,
  title: "测试项目",
  status: "draft",
  scene_json: { objects: [], keyframes: {}, cameraKeyframes: [], shotMarkers: [], shotDescriptions: {}, duration: 5 },
  previs_video_url: "/uploads/videos/previs.mp4",
};

const template = {
  id: 10,
  name: "人物行走模板",
  description: "测试模板",
  scene_json: { objects: [], keyframes: {}, cameraKeyframes: [], shotMarkers: [], shotDescriptions: {}, duration: 5 },
  category: "人物",
  is_builtin: true,
};

function mockListData(projects: unknown[] = [], templates: unknown[] = []) {
  mockedGet.mockImplementation((url: string) => {
    if (url === "/previs/projects") return Promise.resolve({ data: projects });
    if (url === "/previs/templates") return Promise.resolve({ data: templates });
    return Promise.resolve({ data: [] });
  });
}

describe("Workbench", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("加载项目与模板列表", async () => {
    mockListData([project], [template]);

    render(<Workbench />);

    await waitFor(() => expect(screen.getByText("测试项目")).toBeInTheDocument());
    expect(screen.getByText("人物行走模板")).toBeInTheDocument();
  });

  it("文字生成白模会调用 POST /previs/generate", async () => {
    const user = userEvent.setup();
    mockListData([], []);
    mockedPost.mockResolvedValue({
      data: { ...project, scene_json: { objects: [] } },
    });

    render(<Workbench />);

    const input = await screen.findByPlaceholderText("输入成片文案，例如：一只猫在夕阳下奔跑");
    await user.type(input, "一只猫在夕阳下奔跑");
    await user.click(screen.getByRole("button", { name: /文\s*字\s*生\s*成\s*白\s*模/ }));

    expect(mockedPost).toHaveBeenCalledWith(
      "/previs/generate",
      expect.objectContaining({ prompt: "一只猫在夕阳下奔跑" })
    );
  });

  it("点击模板会调用 POST /previs/projects 创建 template 项目", async () => {
    const user = userEvent.setup();
    mockListData([], [template]);
    mockedPost.mockResolvedValue({ data: project });

    render(<Workbench />);

    await screen.findByText("人物行走模板");
    await user.click(screen.getByText("人物行走模板"));

    expect(mockedPost).toHaveBeenCalledWith(
      "/previs/projects",
      expect.objectContaining({ mode: "template", template_id: 10 })
    );
  });

  it("加载带白模视频的项目后批量生成会携带白模参数", async () => {
    const user = userEvent.setup();
    mockListData([project], []);
    mockedPost.mockResolvedValue({ data: { task_ids: [1, 2], count: 2, batch_id: "b" } });

    render(<Workbench />);

    await screen.findByText("测试项目");
    await user.click(screen.getByText("测试项目"));

    const input = await screen.findByPlaceholderText("输入成片文案，例如：一只猫在夕阳下奔跑");
    await user.type(input, "批量测试");
    await user.click(screen.getByRole("button", { name: /批\s*量\s*生\s*成/ }));

    expect(mockedPost).toHaveBeenCalledWith(
      "/generate/batch",
      expect.objectContaining({
        prompt: "批量测试",
        previs_video_url: "/uploads/videos/previs.mp4",
        previs_type: "coarse",
      })
    );
  });

  it("提供上传参考图和参考视频生成白模入口", async () => {
    mockListData([], []);

    render(<Workbench />);

    await screen.findByPlaceholderText("输入成片文案，例如：一只猫在夕阳下奔跑");
    expect(screen.getByRole("button", { name: /上\s*传\s*参\s*考\s*图/ })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /上\s*传\s*参\s*考\s*视\s*频\s*生\s*成\s*白\s*模/ })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /高\s*级.*参\s*考\s*视\s*频\s*生\s*成\s*动\s*态\s*白\s*模/ })
    ).toBeInTheDocument();
  });

  it("保存项目会调用 PUT /previs/projects/{id}", async () => {
    const user = userEvent.setup();
    mockListData([project], []);
    mockedPut.mockResolvedValue({ data: project });

    render(<Workbench />);

    await screen.findByText("测试项目");
    await user.click(screen.getByText("测试项目"));
    await user.click(screen.getByRole("button", { name: /保\s*存\s*项\s*目/ }));

    expect(mockedPut).toHaveBeenCalledWith("/previs/projects/1", expect.any(Object));
  });

  it("删除项目会调用 DELETE /previs/projects/{id}", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    mockListData([project], []);
    mockedDelete.mockResolvedValue({});

    render(<Workbench />);
    await screen.findByText("测试项目");
    await user.click(screen.getByRole("button", { name: /删\s*除/ }));

    expect(mockedDelete).toHaveBeenCalledWith("/previs/projects/1");
    confirmSpy.mockRestore();
  });
});
