import { useCallback, useEffect, useState } from "react";
import { Button, Card, Col, Empty, Form, Input, Row, Space, Typography, Upload, message } from "antd";
import client from "../api/client";

const { Title, Text } = Typography;

interface CharacterItem {
  id: number;
  name: string;
  reference_image_url: string | null;
  description: string | null;
  created_at: string;
}

export default function Characters() {
  const [characters, setCharacters] = useState<CharacterItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [multiViewSubmitting, setMultiViewSubmitting] = useState<number | null>(null);
  const [createForm] = Form.useForm();
  const [multiViewForm] = Form.useForm();
  const [uploadingCreateImage, setUploadingCreateImage] = useState(false);
  const [uploadingMultiViewImage, setUploadingMultiViewImage] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await client.get("/characters");
      setCharacters(response.data);
    } catch {
      message.error("加载角色失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const uploadImage = async (file: File, onSuccess: (url: string) => void) => {
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("file_type", "image");
      const response = await client.post("/upload", formData);
      onSuccess(response.data.file_url);
      message.success("图片已上传");
    } catch {
      message.error("图片上传失败");
    }
  };

  const handleCreate = async (values: { name: string; reference_image_url?: string; description?: string }) => {
    setCreating(true);
    try {
      await client.post("/characters", {
        name: values.name,
        reference_image_url: values.reference_image_url || "",
        description: values.description || "",
      });
      message.success("角色已创建");
      createForm.resetFields();
      load();
    } catch {
      message.error("创建角色失败");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (characterId: number) => {
    if (!window.confirm("确定删除该角色？")) return;
    try {
      await client.delete(`/characters/${characterId}`);
      message.success("角色已删除");
      load();
    } catch {
      message.error("删除角色失败");
    }
  };

  const handleAddMultiView = async (characterId: number, values: { view_name: string; image_url: string }) => {
    setMultiViewSubmitting(characterId);
    try {
      await client.post(`/characters/${characterId}/multi-views`, values);
      message.success("多角度参考图已添加");
      multiViewForm.resetFields();
    } catch {
      message.error("添加多角度参考图失败");
    } finally {
      setMultiViewSubmitting(null);
    }
  };

  return (
    <div>
      <Title level={3}>角色库</Title>
      <Card title="创建角色" style={{ marginBottom: 16 }}>
        <Form form={createForm} layout="inline" onFinish={handleCreate}>
          <Form.Item name="name" rules={[{ required: true, message: "请输入角色名称" }]}>
            <Input placeholder="角色名称" />
          </Form.Item>
          <Form.Item name="reference_image_url">
            <Space.Compact style={{ width: "100%" }}>
              <Input placeholder="参考图 URL（可留空）" style={{ width: 220 }} />
              <Upload
                accept="image/*"
                showUploadList={false}
                beforeUpload={(file) => {
                  setUploadingCreateImage(true);
                  uploadImage(file as File, (url) => {
                    createForm.setFieldValue("reference_image_url", url);
                    setUploadingCreateImage(false);
                  }).finally(() => setUploadingCreateImage(false));
                  return false;
                }}
              >
                <Button loading={uploadingCreateImage}>上传图片</Button>
              </Upload>
            </Space.Compact>
          </Form.Item>
          <Form.Item name="description">
            <Input placeholder="描述（可选）" style={{ width: 200 }} />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={creating}>
            创建
          </Button>
        </Form>
      </Card>

      <Button onClick={load} loading={loading} style={{ marginBottom: 16 }}>
        刷新
      </Button>

      {characters.length === 0 ? (
        <Card>
          <Empty description="暂无角色" />
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          {characters.map((character) => (
            <Col key={character.id} xs={24} sm={12} md={8}>
              <Card
                title={character.name}
                extra={
                  <Space>
                    <Text type="secondary">#{character.id}</Text>
                    <Button size="small" danger onClick={() => handleDelete(character.id)}>
                      删除
                    </Button>
                  </Space>
                }
              >
                {character.reference_image_url ? (
                  <img
                    src={character.reference_image_url}
                    alt={character.name}
                    style={{ width: "100%", maxHeight: 180, objectFit: "cover", borderRadius: 8 }}
                  />
                ) : (
                  <Text type="secondary">暂无参考图</Text>
                )}
                {character.description ? (
                  <ParagraphText text={character.description} />
                ) : null}
                <Form
                  form={multiViewForm}
                  layout="vertical"
                  onFinish={(values) => handleAddMultiView(character.id, values)}
                  style={{ marginTop: 12 }}
                >
                  <Space.Compact style={{ width: "100%" }}>
                    <Form.Item name="view_name" rules={[{ required: true, message: "视角名" }]} style={{ marginBottom: 0 }}>
                      <Input placeholder="视角名，如正面" />
                    </Form.Item>
                    <Form.Item name="image_url" rules={[{ required: true, message: "图片 URL" }]} style={{ marginBottom: 0 }}>
                      <Space.Compact style={{ width: "100%" }}>
                        <Input placeholder="图片 URL" />
                        <Upload
                          accept="image/*"
                          showUploadList={false}
                          beforeUpload={(file) => {
                            setUploadingMultiViewImage(true);
                            uploadImage(file as File, (url) => {
                              multiViewForm.setFieldValue("image_url", url);
                              setUploadingMultiViewImage(false);
                            }).finally(() => setUploadingMultiViewImage(false));
                            return false;
                          }}
                        >
                          <Button loading={uploadingMultiViewImage}>上传</Button>
                        </Upload>
                      </Space.Compact>
                    </Form.Item>
                    <Button htmlType="submit" loading={multiViewSubmitting === character.id}>
                      添加视角
                    </Button>
                  </Space.Compact>
                </Form>
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  );
}

function ParagraphText({ text }: { text: string }) {
  return (
    <Text type="secondary" style={{ display: "block", marginTop: 8 }}>
      {text}
    </Text>
  );
}
