import { useState } from "react";
import { Button, Card, Col, List, Row, Space, Typography, message } from "antd";
import client from "../api/client";
import EditorToolbar from "../components/EditorToolbar";
import PrevisCanvas from "../components/PrevisCanvas";
import Timeline from "../components/Timeline";
import { usePrevisStore } from "../previs/store";

const { Title, Paragraph } = Typography;

export default function Workbench() {
  const [projectId, setProjectId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const objects = usePrevisStore((state) => state.objects);
  const selectedObjectId = usePrevisStore((state) => state.selectedObjectId);
  const selectObject = usePrevisStore((state) => state.selectObject);

  const handleSave = async (scene: unknown) => {
    setSaving(true);
    try {
      if (projectId === null) {
        const response = await client.post("/previs/projects", {
          title: "未命名白模项目",
          mode: "manual",
          scene_json: scene,
        });
        setProjectId(response.data.id);
        message.success("白模项目已创建");
      } else {
        await client.put(`/previs/projects/${projectId}`, { scene_json: scene });
        message.success("白模项目已保存");
      }
    } catch (error) {
      message.error("保存失败，请检查登录状态");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <Title level={3}>创作工作台</Title>
      <Paragraph>第一版重点：自由建模 + 关键帧动画，后续接入白模生成与 AI 成片。</Paragraph>
      <Row gutter={16}>
        <Col span={10}>
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
            <PrevisCanvas />
            <Timeline />
          </Card>
        </Col>
        <Col span={14}>
          <Card title="提示">
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
