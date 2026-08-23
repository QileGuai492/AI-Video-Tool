import { useEffect, useState } from "react";
import { Alert, Button, Card, Col, Divider, Input, InputNumber, List, Row, Segmented, Select, Space, Switch, Typography, Upload, message } from "antd";
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

interface PrevisTemplateItem {
  id: number;
  name: string;
  description: string | null;
  scene_json: SceneState;
  category: string | null;
  is_builtin: boolean;
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
  const [templates, setTemplates] = useState<PrevisTemplateItem[]>([]);
  const [editorMode, setEditorMode] = useState<"simple" | "advanced">("advanced");
  const [generatingPrevis, setGeneratingPrevis] = useState(false);
  const [generatingFromVideo, setGeneratingFromVideo] = useState(false);
  const [generatingFromVideoAdvanced, setGeneratingFromVideoAdvanced] = useState(false);
  const [batchCount, setBatchCount] = useState(2);
  const [batchSubmitting, setBatchSubmitting] = useState(false);
  const [referenceImages, setReferenceImages] = useState<string[]>([]);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [voiceId, setVoiceId] = useState<string | undefined>(undefined);
  const [withSubtitle, setWithSubtitle] = useState(true);
  const [speechText, setSpeechText] = useState("");
  const [characters, setCharacters] = useState<{ id: number; name: string }[]>([]);
  const [characterMappings, setCharacterMappings] = useState<Record<string, number | undefined>>({});
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

  const loadTemplates = async () => {
    try {
      const response = await client.get("/previs/templates");
      setTemplates(response.data);
    } catch {
      // 忽略
    }
  };

  useEffect(() => {
    loadProjects();
    loadTemplates();
    client
      .get("/characters")
      .then((response) => setCharacters(response.data))
      .catch(() => {
        // 忽略角色加载失败
      });
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

  const buildSceneCameraScript = (scene: SceneState) => {
    const markers = [
      0,
      ...(scene.shotMarkers ?? []).filter((marker) => marker > 0 && marker < scene.duration),
      scene.duration,
    ].sort((a, b) => a - b);
    const shots = markers.slice(0, -1).map((start, index) => {
      const description = (scene.shotDescriptions ?? {})[start] ?? { action: "", camera: "" };
      return {
        start,
        end: markers[index + 1],
        action: description.action,
        camera: description.camera,
      };
    });
    return { shots };
  };

  const handleDeleteProject = async (id: number) => {
    if (!window.confirm("确定删除该项目？")) return;
    try {
      await client.delete(`/previs/projects/${id}`);
      message.success("项目已删除");
      if (projectId === id) {
        setProjectId(null);
        setPrevisVideoUrl(null);
        loadScene(emptyScene);
      }
      await loadProjects();
    } catch {
      message.error("删除项目失败");
    }
  };

  const handleDeleteTemplate = async (id: number) => {
    if (!window.confirm("确定删除该模板？")) return;
    try {
      await client.delete(`/previs/templates/${id}`);
      message.success("模板已删除");
      await loadTemplates();
    } catch {
      message.error("删除模板失败");
    }
  };

  const handleUseTemplate = async (template: PrevisTemplateItem) => {
    try {
      const scene = template.scene_json ?? emptyScene;
      const response = await client.post("/previs/projects", {
        title: template.name,
        mode: "template",
        template_id: template.id,
        scene_json: scene,
        camera_script: buildSceneCameraScript(scene),
      });
      const project = response.data;
      setProjectId(project.id);
      setPrevisVideoUrl(project.previs_video_url);
      loadScene(scene);
      await loadProjects();
      message.success(`已从模板创建项目：${template.name}`);
    } catch (error) {
      console.error("使用模板失败", error);
      message.error("使用模板失败，请检查登录状态");
    }
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
      const response = (error as { response?: { status?: number; data?: unknown } })?.response;
      const data = response?.data;
      const detail =
        (data as { detail?: string } | undefined)?.detail ??
        (typeof data === "string" ? data : data ? JSON.stringify(data) : undefined) ??
        (error as Error)?.message ??
        "请检查后端与 PUBLIC_BASE_URL 配置";
      message.error(`白模视频上传失败${response?.status ? `（${response.status}）` : ""}：${detail}`);
    }
  };

  const handleUploadImage = async (file: File) => {
    setUploadingImage(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("file_type", "image");
      const response = await client.post("/upload", formData);
      setReferenceImages((prev) => [...prev, response.data.file_url]);
      message.success("参考图已上传");
    } catch {
      message.error("参考图上传失败");
    } finally {
      setUploadingImage(false);
    }
  };

  const handleSubmitGenerate = async () => {
    if (!previsVideoUrl && referenceImages.length === 0) {
      message.warning("请先上传参考图或录制白模视频");
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
        image_url: referenceImages[0] ?? null,
        reference_image_urls: referenceImages.length > 0 ? referenceImages : null,
        previs_video_url: previsVideoUrl,
        previs_type: previsVideoUrl ? "coarse" : null,
        camera_script: buildCameraScript(),
        duration: 5,
        aspect_ratio: "16:9",
        quality: "standard",
        character_mappings: characterMappingsPayload.length > 0 ? characterMappingsPayload : null,
        voice_id: voiceId,
        with_subtitle: withSubtitle,
        speech_text: speechText.trim() || null,
      });
      message.success(`AI 生成任务已提交，任务 ID：${response.data.id}`);
    } catch (error) {
      message.error("AI 生成任务提交失败");
    } finally {
      setSubmitting(false);
    }
  };

  const handleBatchGenerate = async () => {
    if (!previsVideoUrl && referenceImages.length === 0) {
      message.warning("请先上传参考图或录制白模视频");
      return;
    }
    if (!prompt.trim()) {
      message.warning("请输入成片文案");
      return;
    }
    setBatchSubmitting(true);
    try {
      const response = await client.post("/generate/batch", {
        prompt: prompt.trim(),
        count: batchCount,
        image_url: referenceImages[0] ?? null,
        reference_image_urls: referenceImages.length > 0 ? referenceImages : null,
        previs_video_url: previsVideoUrl,
        previs_type: previsVideoUrl ? "coarse" : null,
        camera_script: buildCameraScript(),
        duration: 5,
        aspect_ratio: "16:9",
        quality: "standard",
        character_mappings: characterMappingsPayload.length > 0 ? characterMappingsPayload : null,
        voice_id: voiceId,
        with_subtitle: withSubtitle,
        speech_text: speechText.trim() || null,
      });
      message.success(`已提交 ${response.data.count} 个批量任务，可到任务中心查看`);
    } catch (error) {
      console.error("批量生成失败", error);
      message.error("批量生成失败，请检查后端配置");
    } finally {
      setBatchSubmitting(false);
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

  const handleGenerateFromVideo = async (file: File) => {
    setGeneratingFromVideo(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (prompt.trim()) {
        formData.append("prompt", prompt.trim());
      }
      formData.append("title", prompt.trim().slice(0, 20) || "参考视频白模");
      const response = await client.post("/previs/generate-from-video", formData);
      const project = response.data;
      setProjectId(project.id);
      setPrevisVideoUrl(project.previs_video_url);
      loadScene(project.scene_json ?? emptyScene);
      await loadProjects();
      message.success("已根据参考视频生成白模项目");
    } catch (error) {
      console.error("参考视频生成白模失败", error);
      message.error("参考视频生成白模失败，请检查后端与 LLM 配置");
    } finally {
      setGeneratingFromVideo(false);
    }
  };

  const handleGenerateFromVideoAdvanced = async (file: File) => {
    setGeneratingFromVideoAdvanced(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (prompt.trim()) {
        formData.append("prompt", prompt.trim());
      }
      formData.append("title", prompt.trim().slice(0, 20) || "参考视频动态白模");
      const response = await client.post("/previs/generate-from-video-advanced", formData);
      const project = response.data;
      setProjectId(project.id);
      setPrevisVideoUrl(project.previs_video_url);
      loadScene(project.scene_json ?? emptyScene);
      await loadProjects();
      message.success("已根据参考视频生成动态白模项目");
    } catch (error) {
      console.error("参考视频生成动态白模失败", error);
      message.error("参考视频生成动态白模失败，请检查后端与 LLM 配置");
    } finally {
      setGeneratingFromVideoAdvanced(false);
    }
  };

  const shotStarts = [0, ...shotMarkers.filter((marker) => marker > 0 && marker < duration), duration].sort(
    (a, b) => a - b
  );

  const humanoidObjects = objects.filter((obj) => obj.type === "humanoid");
  const characterLabels: Record<string, string> = {};
  for (const [objectId, selectedCharacterId] of Object.entries(characterMappings)) {
    const character = characters.find((item) => item.id === selectedCharacterId);
    if (character) characterLabels[objectId] = character.name;
  }
  const characterMappingsPayload = Object.entries(characterMappings)
    .filter(([, selectedCharacterId]) => selectedCharacterId != null)
    .map(([objectId, selectedCharacterId]) => ({
      object_id: objectId,
      character_id: selectedCharacterId,
    }));

  return (
    <div>
      <Title level={3} style={{ marginBottom: 4 }}>
        创作工作台
      </Title>
      <Paragraph type="secondary">自由建模 → 关键帧动画 → 白模视频 → AI 成片</Paragraph>
      <Row gutter={16}>
        {/* 左侧：项目 / 对象 / 属性 / 关键帧 */}
        <Col xs={24} lg={5}>
          <Card
            title="项目"
            size="small"
            extra={<Button size="small" onClick={handleNewProject}>新建</Button>}
          >
            {projects.length === 0 ? (
              <Text type="secondary">暂无项目</Text>
            ) : (
              <div style={{ maxHeight: 340, overflowY: "auto" }}>
                <List
                  size="small"
                  dataSource={projects}
                  renderItem={(project) => (
                    <List.Item
                      style={{ cursor: "pointer", padding: "6px 0" }}
                      onClick={() => handleLoadProject(project)}
                      actions={[
                        <Button
                          key="delete"
                          size="small"
                          danger
                          onClick={(event) => {
                            event.stopPropagation();
                            handleDeleteProject(project.id);
                          }}
                        >
                          删除
                        </Button>,
                      ]}
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
              </div>
            )}
          </Card>
          <Card title="模板" size="small" style={{ marginTop: 12 }}>
            {templates.length === 0 ? (
              <Text type="secondary">暂无模板</Text>
            ) : (
              <div style={{ maxHeight: 340, overflowY: "auto" }}>
                <List
                  size="small"
                  dataSource={templates}
                  renderItem={(template) => (
                    <List.Item
                      style={{ cursor: "pointer", padding: "6px 0" }}
                      onClick={() => handleUseTemplate(template)}
                      actions={
                        template.is_builtin
                          ? undefined
                          : [
                              <Button
                                key="delete"
                                size="small"
                                danger
                                onClick={(event) => {
                                  event.stopPropagation();
                                  handleDeleteTemplate(template.id);
                                }}
                              >
                                删除
                              </Button>,
                            ]
                      }
                    >
                      <Space direction="vertical" size={0}>
                        <Text>{template.name}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {template.description}
                        </Text>
                      </Space>
                    </List.Item>
                  )}
                />
              </div>
            )}
          </Card>
        </Col>

        {/* 中间：3D 编辑器 */}
        <Col xs={24} lg={12}>
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
            <Row gutter={12} style={{ marginBottom: 12 }}>
              <Col xs={24} md={10}>
                <Card title="对象" size="small">
                  {objects.length === 0 ? (
                    <Text type="secondary">暂无对象</Text>
                  ) : (
                    <div style={{ maxHeight: 180, overflowY: "auto" }}>
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
                    </div>
                  )}
                </Card>
              </Col>
              <Col xs={24} md={14}>
                <ObjectProperties />
              </Col>
            </Row>
            <PrevisCanvas onRecorded={handleRecorded} characterLabels={characterLabels} />
            <Timeline />
            <div style={{ marginTop: 12 }}>
              <KeyframeList />
            </div>
          </Card>
        </Col>

        {/* 右侧：AI 成片 / 镜头描述 */}
        <Col xs={24} lg={7}>
          <Card title="AI 成片" size="small">
            <Text strong>成片文案</Text>
            <Input.TextArea
              rows={4}
              style={{ marginTop: 8 }}
              placeholder="输入成片文案，例如：一只猫在夕阳下奔跑"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
            />
            <Divider style={{ margin: "16px 0" }} />
            <Text strong>参考素材</Text>
            <Space direction="vertical" style={{ width: "100%", marginTop: 8 }}>
              <Upload
                accept="image/*"
                showUploadList={false}
                style={{ width: "100%" }}
                beforeUpload={(file) => {
                  handleUploadImage(file as File);
                  return false;
                }}
              >
                <Button block loading={uploadingImage}>
                  {referenceImages.length > 0 ? "继续上传参考图" : "上传参考图"}
                </Button>
              </Upload>
              {referenceImages.length > 0 ? (
                <Space wrap style={{ width: "100%" }}>
                  {referenceImages.map((url, index) => (
                    <Space key={url} direction="vertical" size={2} style={{ textAlign: "center" }}>
                      <img
                        src={url}
                        alt={`参考图${index + 1}`}
                        style={{ width: 64, height: 64, objectFit: "cover", borderRadius: 8 }}
                      />
                      <Button
                        size="small"
                        type="text"
                        danger
                        onClick={() => setReferenceImages((prev) => prev.filter((item) => item !== url))}
                      >
                        移除
                      </Button>
                    </Space>
                  ))}
                </Space>
              ) : null}
              <Upload
                accept="video/*"
                showUploadList={false}
                style={{ width: "100%" }}
                beforeUpload={(file) => {
                  handleGenerateFromVideo(file as File);
                  return false;
                }}
              >
                <Button block loading={generatingFromVideo}>
                  上传参考视频生成白模
                </Button>
              </Upload>
              <Upload
                accept="video/*"
                showUploadList={false}
                style={{ width: "100%" }}
                beforeUpload={(file) => {
                  handleGenerateFromVideoAdvanced(file as File);
                  return false;
                }}
              >
                <Button block loading={generatingFromVideoAdvanced}>
                  高级：参考视频生成动态白模
                </Button>
              </Upload>
            </Space>
            {humanoidObjects.length > 0 ? (
              <>
                <Divider style={{ margin: "16px 0" }} />
                <Text strong>角色映射</Text>
                <Space direction="vertical" style={{ width: "100%", marginTop: 8 }}>
                  {humanoidObjects.map((obj) => (
                    <Space key={obj.id} style={{ width: "100%", justifyContent: "space-between" }}>
                      <Text style={{ flex: 1 }}>{obj.name}</Text>
                      <Select
                        allowClear
                        placeholder="选择角色"
                        style={{ width: 150 }}
                        value={characterMappings[obj.id]}
                        onChange={(value) =>
                          setCharacterMappings((prev) => ({ ...prev, [obj.id]: value }))
                        }
                        options={characters.map((character) => ({
                          value: character.id,
                          label: character.name,
                        }))}
                      />
                    </Space>
                  ))}
                </Space>
              </>
            ) : null}
            <Divider style={{ margin: "16px 0" }} />
            <Text strong>生成操作</Text>
            <Space direction="vertical" style={{ width: "100%", marginTop: 8 }}>
              <Input.TextArea
                rows={2}
                placeholder="台词/配音文本（留空则自动提取文案中的引号内容）"
                value={speechText}
                onChange={(event) => setSpeechText(event.target.value)}
              />
              <Space.Compact block>
                <Select
                  allowClear
                  placeholder="配音音色"
                  style={{ width: "100%" }}
                  value={voiceId}
                  onChange={setVoiceId}
                  options={[
                    { value: "female_01", label: "女声（默认）" },
                    { value: "male_01", label: "男声" },
                  ]}
                />
              </Space.Compact>
              <Space style={{ width: "100%", justifyContent: "space-between" }}>
                <Text>添加字幕</Text>
                <Switch checked={withSubtitle} onChange={setWithSubtitle} />
              </Space>
              <Button block loading={generatingPrevis} onClick={handleGeneratePrevis}>
                文字生成白模
              </Button>
              <Space.Compact block>
                <InputNumber
                  min={1}
                  max={5}
                  value={batchCount}
                  onChange={(value) => setBatchCount(value ?? 2)}
                  style={{ width: 80 }}
                />
                <Button block loading={batchSubmitting} onClick={handleBatchGenerate}>
                  批量生成
                </Button>
              </Space.Compact>
              <Button block onClick={() => { window.location.href = "/tasks"; }}>
                查看任务中心
              </Button>
              <Button type="primary" block loading={submitting} onClick={handleSubmitGenerate}>
                提交 AI 生成
              </Button>
              <Text type="secondary" style={{ fontSize: 12, textAlign: "center" }}>
                {previsVideoUrl
                  ? "白模视频已就绪，可以提交生成"
                  : referenceImages.length > 0
                    ? "参考图已就绪，可以提交生成"
                    : "请上传参考图或录制白模视频"}
              </Text>
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
