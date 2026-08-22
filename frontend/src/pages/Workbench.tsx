import { useEffect, useState } from "react";
import { Button, Card, Col, Input, List, Row, Space, Typography, message } from "antd";
import client from "../api/client";
import EditorToolbar from "../components/EditorToolbar";
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
  duration: 5,
};

export default function Workbench() {
  const [projectId, setProjectId] = useState<number | null>(null);
  const [previsVideoUrl, setPrevisVideoUrl] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("");
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [projects, setProjects] = useState<PrevisProjectItem[]>([]);
  const objects = usePrevisStore((state) => state.objects);
  const selectedObjectId = usePrevisStore((state) => state.selectedObjectId);
  const selectObject = usePrevisStore((state) => state.selectObject);
  const loadScene = usePrevisStore((state) => state.loadScene);

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

  const ensureProject = async (scene: unknown): Promise<number> => {
    if (projectId !== null) return projectId;
    const response = await client.post("/previs/projects", {
      title: "未命名白模项目",
      mode: "manual",
      scene_json: scene,
    });
    setProjectId(response.data.id);
    await loadProjects();
    return response.data.id as number;
  };

  const handleSave = async (scene: unknown) => {
    setSaving(true);
    try {
      const id = await ensureProject(scene);
      await client.put(`/previs/projects/${id}`, { scene_json: scene });
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
      message.error("白模视频上传失败");
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

  return (
    <div>
      <Title level={3}>创作工作台</Title>
      <Paragraph>第一版重点：自由建模 + 关键帧动画，后续接入白模生成与 AI 成片。</Paragraph>
      <Row gutter={16}>
        <Col span={10}>
          <Card
            title="我的白模项目"
            style={{ marginBottom: 16 }}
            extra={<Button size="small" onClick={handleNewProject}>新建</Button>}
          >
            {projects.length === 0 ? (
              <Paragraph type="secondary">暂无项目</Paragraph>
            ) : (
              <List
                size="small"
                dataSource={projects}
                renderItem={(project) => (
                  <List.Item
                    style={{ cursor: "pointer" }}
                    onClick={() => handleLoadProject(project)}
                  >
                    {project.title}
                    <Text type="secondary">（{project.status}）</Text>
                  </List.Item>
                )}
              />
            )}
          </Card>
          <Card title="对象列表" style={{ marginBottom: 16 }}>
            {objects.length === 0 ? (
              <Paragraph type="secondary">暂无对象，请从上方工具栏添加。</Paragraph>
            ) : (
              <List
                size="small"
                dataSource={objects}
                renderItem={(obj) => (
                  <List.Item
                    style={{ cursor: "pointer" }}
                    onClick={() => selectObject(obj.id)}
                    className={obj.id === selectedObjectId ? "ant-list-item-selected" : ""}
                  >
                    {obj.name}
                  </List.Item>
                )}
              />
            )}
          </Card>
          <Card title="白模编辑">
            <EditorToolbar onSave={handleSave} />
            <PrevisCanvas onRecorded={handleRecorded} />
            <Timeline />
          </Card>
        </Col>
        <Col span={14}>
          <Card title="AI 成片">
            <Input.TextArea
              rows={4}
              placeholder="输入成片文案，例如：一只猫在夕阳下奔跑"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
            />
            <Space direction="vertical" style={{ width: "100%", marginTop: 16 }}>
              <Text type="secondary">
                {previsVideoUrl ? "白模视频已就绪，可以提交生成" : "请先录制白模视频"}
              </Text>
              <Button type="primary" block loading={submitting} onClick={handleSubmitGenerate}>
                提交 AI 生成
              </Button>
            </Space>
          </Card>
          <Card title="提示" style={{ marginTop: 16 }}>
            <Paragraph>
              1. 添加方块/圆柱/球体/平面/灰模人形。
              <br />
              2. 点击对象列表选中对象。
              <br />
              3. 使用 Gizmo 移动/旋转/缩放。
              <br />
              4. 在时间轴拖动到目标时间，点击“记录关键帧”。
              <br />
              5. 点击“记录相机”保存当前相机关键帧。
              <br />
              6. 点击“播放”预览动画。
              <br />
              7. 点击“录制视频”，完成后自动上传并转 MP4。
              <br />
              8. 填写文案后点击“提交 AI 生成”。
            </Paragraph>
          </Card>
        </Col>
      </Row>
      {projectId && (
        <Space style={{ marginTop: 8 }}>
          <Button loading={saving} onClick={() => handleSave(usePrevisStore.getState().exportScene())}>
            再次保存
          </Button>
        </Space>
      )}
    </div>
  );
}
