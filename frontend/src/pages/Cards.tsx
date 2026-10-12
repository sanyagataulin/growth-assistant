import { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Card,
  Col,
  Form,
  InputNumber,
  Modal,
  Progress,
  Row,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd'
import { EditOutlined } from '@ant-design/icons'
import { api } from '../api'
import type { CardRow } from '../types'

export function Cards() {
  const [rows, setRows] = useState<CardRow[] | null>(null)
  const [editing, setEditing] = useState<CardRow | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm<{ price: number; photo_count: number; description_len: number }>()

  const load = useCallback(() => {
    api<CardRow[]>('/cabinet/cards').then(setRows)
  }, [])

  useEffect(load, [load])

  const openEditor = (r: CardRow) => {
    setEditing(r)
    form.setFieldsValue({ price: r.price, photo_count: r.photo_count, description_len: r.description_len })
  }

  const save = async () => {
    if (!editing) return
    const values = await form.validateFields()
    setSaving(true)
    try {
      await api(`/cabinet/products/${editing.id}`, { method: 'PATCH', json: values })
      message.success(`Карточка «${editing.name}» обновлена — помощник увидит это при следующем расчёте`)
      setEditing(null)
      load()
    } catch (e) {
      message.error(e instanceof Error ? e.message : 'Не удалось сохранить карточку')
    } finally {
      setSaving(false)
    }
  }

  if (!rows) return <Spin size="large" style={{ display: 'block', margin: '64px auto' }} />

  const worst = rows.filter((r) => r.quality < 70)

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={4} style={{ margin: 0 }}>
        Карточки товаров
      </Typography.Title>
      {worst.length > 0 && (
        <Typography.Text type="warning">
          ⚠️ {worst.length} карточк(и) с низким качеством — помощник предложит усилить слабейшие
        </Typography.Text>
      )}
      <Row gutter={[16, 16]}>
        {rows.map((r) => (
          <Col key={r.id} span={6}>
            <Card
              size="small"
              title={r.name}
              extra={<Tag>{r.category}</Tag>}
              actions={[
                <Typography.Text key="c" type="secondary">
                  CTR {r.ctr}% · {r.views_14d} просмотров
                </Typography.Text>,
                <Button key="e" type="text" icon={<EditOutlined />} onClick={() => openEditor(r)}>
                  Редактировать
                </Button>,
              ]}
            >
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <Progress
                  type="circle"
                  size={64}
                  percent={r.quality}
                  strokeColor={r.quality >= 70 ? '#389e0d' : r.quality >= 45 ? '#faad14' : '#f5222d'}
                />
                <div style={{ fontSize: 13, color: '#666' }}>
                  <div>📷 фото: {r.photo_count} {r.photo_count < 3 && '⚠️'}</div>
                  <div>📝 описание: {r.description_len} зн. {r.description_len < 200 && '⚠️'}</div>
                  <div>🛒 в корзину: {r.cart_14d}</div>
                </div>
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      <Modal
        open={editing !== null}
        title={`Редактировать карточку: ${editing?.name ?? ''}`}
        onCancel={() => setEditing(null)}
        onOk={save}
        okText="Сохранить"
        confirmLoading={saving}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="photo_count"
            label="Фото в карточке"
            extra="Норма маркетплейса — от 3 фото"
          >
            <InputNumber min={0} max={20} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item
            name="description_len"
            label="Описание, знаков"
            extra="Норма — от 400 знаков; в прототипе хранится длина описания"
          >
            <InputNumber min={0} max={5000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="price" label="Цена, ₽">
            <InputNumber min={0.5} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
