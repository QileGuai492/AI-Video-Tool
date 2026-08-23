import { useEffect, useState } from "react";
import { Alert, Button, Card, Col, Input, List, Row, Segmented, Space, Typography, message } from "antd";
import client from "../api/client";
import EditorToolbar from "../components/EditorToolbar";
import KeyframeList from "../components/KeyframeList";
import ObjectProperties from "../components/ObjectProperties";
import PrevisCanvas from "../components/PrevisCanvas";
import Timeline from "../components/Timeline";
import { usePrevisStore } from "../previs/store";
import type { SceneState } from "../previs/types";

const { Title, Paragraph, Text } = Typography;

interface PrevisProjectItem {
  id: number;
  title: string;
  status: string;
  scene_json: SceneState;
  previs_video_url: string | null;
}

const emptyScene: SceneState = {
  objects: [],
  keyframes: {},
  cameraKeyframes: [],
  shotMarkers: [],
  shotDescriptions: {},
  duration: 5,
};

export default function Workbench() {
  const [projectId, setProjectId] = useState<number | null>(null);
  const [previsVideoUrl, setPrevisVideoUrl] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [projects, setProjects] = useState<PrevisProjectItem[]>([]);
  const [editorMode, setEditorMode] = useState<"simple" | "advanced">("advanced");
  const [generatingPrevis, setGeneratingPrevis] = useState(false);
  const objects = usePrevisStore((state) => state.objects);
  const selectedObjectId = usePrevisStore((state) => state.selectedObjectId);
  const shotMarkers = usePrevisStore((state) => state.shotMarkers);
  const shotDescriptions = usePrevisStore((state) => state.shotDescriptions);
  const duration = usePrevisStore((state) => state.duration);
  const selectObject = usePrevisStore((state) => state.selectObject);
  const loadScene = usePrevisStore((state) => state.loadScene);
  const setShotDescription = usePrevisStore((state) => state.setShotDescription);

  const loadProjects = async () => {
    try {
      const response = await client.get("/previs/projects");
      setProjects(response.data);
    } catch {
      // 忽略
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleLoadProject = (project: PrevisProjectItem) => {
    setProjectId(project.id);
    setPrevisVideoUrl(project.previs_video_url);
    loadScene(project.scene_json ?? emptyScene);
    message.success(`已加载项目：${project.title}`);
  };

  const handleNewProject = () => {
    setProjectId(null);
    setPrevisVideoUrl(null);
    loadScene(emptyScene);
  };

  const buildCameraScript = () => {
    const markers = [0, ...shotMarkers.filter((marker) => marker > 0 && marker < duration), duration].sort(
      (a, b) => a - b
    );
    const shots = markers.slice(0, -1).map((start, index) => {
      const description = shotDescriptions[start] ?? { action: "", camera: "" };
      return {
        start,
        end: markers[index + 1],
        action: description.action,
        camera: description.camera,
      };
    });
    return { shots };
  };

  const ensureProject = async (scene: unknown): Promise<number> => {
    if (projectId !== null) return projectId;
    const response = await client.post("/previs/projects", {
      title: "未命名白模项目",
      mode: "manual",
      scene_json: scene,
      camera_script: buildCameraScript(),
    });
    setProjectId(response.data.id);
    await loadProjects();
    return response.data.id as number;
  };

  const handleSave = async (scene: unknown) => {
    setSaving(true);
    try {
      const id = await ensureProject(scene);
      await client.put(`/previs/projects/${id}`, {
        scene_json: scene,
        camera_script: buildCameraScript(),
      });
      message.success("白模项目已保存");
    } catch (error) {
      message.error("保存失败，请检查登录状态");
    } finally {
      setSaving(false);
    }
  };

  const handleRecorded = async (blob: Blob) => {
    try {
      const id = await ensureProject(usePrevisStore.getState().exportScene());
      const formData = new FormData();
      formData.append("file", blob, "previs.webm");
      const response = await client.post(`/previs/projects/${id}/video`, formData);
      setPrevisVideoUrl(response.data.previs_video_url);
      message.success("白模视频已上传并转 MP4");
    } catch (error) {
      console.error("白模视频上传失败", error);
      message.error("白模视频上传失败，请检查后端与 PUBLIC_BASE_URL 配置");
    }
  };

  const handleSubmitGenerate = async () => {
    if (!previsVideoUrl) {
      message.warning("请先录制并上传白模视频");
      return;
    }
    if (!prompt.trim()) {
      message.warning("请输入成片文案");
      return;
    }
    setSubmitting(true);
    try {
      const response = await client.post("/generate/video", {
        prompt: prompt.trim(),
        previs_video_url: previsVideoUrl,
        previs_type: "coarse",
        camera_script: buildCameraScript(),
        duration: 5,
        aspect_ratio: "16:9",
        quality: "standard",
      });
      message.success(`AI 生成任务已提交，任务 ID：${response.data.id}`);
    } catch (error) {
      message.error("AI 生成任务提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleGeneratePrevis = async () => {
    if (!prompt.trim()) {
      message.warning("请先输入文案");
      return;
    }
    setGeneratingPrevis(true);
    try {
      const response = await client.post("/previs/generate", {
        prompt: prompt.trim(),
        title: prompt.trim().slice(0, 20),
      });
      const project = response.data;
      setProjectId(project.id);
      setPrevisVideoUrl(project.previs_video_url);
      loadScene(project.scene_json ?? emptyScene);
      await loadProjects();
      message.success("已根据文案生成白模项目");
    } catch (error) {
      console.error("文字生成白模失败", error);
      message.error("文字生成白模失败，请检查后端与 LLM 配置");
    } finally {
      setGeneratingPrevis(false);
    }
  };

  const shotStarts = [0, ...shotMarkers.filter((marker) => marker > 0 && marker < duration), duration].sort(
    (a, b) => a - b
  );

  return (
    <div>
      <Title level={3} style={{ marginBottom: 4 }}>
        创作工作台
      </Title>
      <Paragraph type="secondary">自由建模 → 关键帧动画 → 白模视频 → AI 成片</Paragraph>
      <Row gutter={16}>
        {/* 左侧：项目 / 对象 / 属性 / 关键帧 */}
        <Col span={5}>
          <Card
            title="项目"
            size="small"
            extra={<Button size="small" onClick={handleNewProject}>新建</Button>}
          >
            {projects.length === 0 ? (
              <Text type="secondary">暂无项目</Text>
            ) : (
              <List
                size="small"
                dataSource={projects}
                renderItem={(project) => (
                  <List.Item
                    style={{ cursor: "pointer", padding: "6px 0" }}
                    onClick={() => handleLoadProject(project)}
                  >
                    <Space direction="vertical" size={0}>
                      <Text>{project.title}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {project.status}
                      </Text>
                    </Space>
                  </List.Item>
                )}
              />
            )}
          </Card>
          <Card title="对象" size="small" style={{ marginTop: 12 }}>
            {objects.length === 0 ? (
              <Text type="secondary">暂无对象</Text>
            ) : (
              <List
                size="small"
                dataSource={objects}
                renderItem={(obj) => (
                  <List.Item
                    style={{ cursor: "pointer", padding: "6px 0" }}
                    onClick={() => selectObject(obj.id)}
                    className={obj.id === selectedObjectId ? "ant-list-item-selected" : ""}
                  >
                    {obj.name}
                  </List.Item>
                )}
              />
            )}
          </Card>
          <div style={{ marginTop: 12 }}>
            <ObjectProperties />
          </div>
          <div style={{ marginTop: 12 }}>
            <KeyframeList />
          </div>
        </Col>

        {/* 中间：3D 编辑器 */}
        <Col span={12}>
          <Card
            title="白模编辑"
            size="small"
            extra={
              <Segmented
                options={[
                  { label: "简单", value: "simple" },
                  { label: "高级", value: "advanced" },
                ]}
                value={editorMode}
                onChange={(value) => setEditorMode(value as "simple" | "advanced")}
              />
            }
          >
            <EditorToolbar mode={editorMode} onSave={handleSave} />
            <PrevisCanvas onRecorded={handleRecorded} />
            <Timeline />
          </Card>
        </Col>

        {/* 右侧：AI 成片 / 镜头描述 */}
        <Col span={7}>
          <Card title="AI 成片" size="small">
            <Input.TextArea
              rows={4}
              placeholder="输入成片文案，例如：一只猫在夕阳下奔跑"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
            />
            <Space direction="vertical" style={{ width: "100%", marginTop: 12 }}>
              <Text type="secondary">
                {previsVideoUrl ? "白模视频已就绪，可以提交生成" : "请先录制白模视频"}
              </Text>
              <Button block loading={generatingPrevis} onClick={handleGeneratePrevis}>
                文字生成白模
              </Button>
              <Button type="primary" block loading={submitting} onClick={handleSubmitGenerate}>
                提交 AI 生成
              </Button>
            </Space>
          </Card>
          <Card title="镜头描述" size="small" style={{ marginTop: 12 }}>
            {shotStarts.length <= 1 ? (
              <Text type="secondary">请先在时间轴添加镜头切点</Text>
            ) : (
              <Space direction="vertical" style={{ width: "100%" }}>
                {shotStarts.slice(0, -1).map((start, index) => {
                  const description = shotDescriptions[start] ?? { action: "", camera: "" };
                  return (
                    <Space key={start} direction="vertical" style={{ width: "100%" }}>
                      <Text strong>
                        镜头 {index + 1}（{start.toFixed(1)}s - {shotStarts[index + 1].toFixed(1)}s）
                      </Text>
                      <Input
                        placeholder="动作描述"
                        value={description.action}
                        onChange={(event) =>
                          setShotDescription(start, { ...description, action: event.target.value })
                        }
                      />
                      <Input
                        placeholder="运镜描述"
                        value={description.camera}
                        onChange={(event) =>
                          setShotDescription(start, { ...description, camera: event.target.value })
                        }
                      />
                    </Space>
                  );
                })}
              </Space>
            )}
          </Card>
          {projectId && (
            <Button
              loading={saving}
              block
              style={{ marginTop: 12 }}
              onClick={() => handleSave(usePrevisStore.getState().exportScene())}
            >
              保存项目
            </Button>
          )}
        </Col>
      </Row>
      <Alert
        style={{ marginTop: 16 }}
        type="info"
        showIcon
        message="使用提示"
        description="添加对象后，在左侧对象列表选中；使用 Gizmo 调整变换；在时间轴记录关键帧与镜头切点；点击“录制视频”上传白模，再填写文案提交 AI 生成。"
      />
    </div>
  );
}
