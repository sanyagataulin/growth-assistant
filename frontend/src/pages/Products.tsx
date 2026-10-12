import { useCallback, useEffect, useState } from 'react'
import {
  AutoComplete,
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Spin,
  Table,
  Tag,
  Typography,
  message,
} from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import { api } from '../api'
import type { ProductRow } from '../types'

const UNITS = ['шт', 'кг', 'л', 'уп', 'бух', 'б', 'фл', 'дес']

interface ProductFormValues {
  name: string
  category: string
  unit: string
  price: number
  cost: number
  stock: number
  expires_at?: Dayjs
  photo_count: number
  description_len: number
  views_14d: number
  cart_14d: number
}

export function Products() {
  const [rows, setRows] = useState<ProductRow[] | null>(null)
  const [open, setOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm<ProductFormValues>()

  const load = useCallback(() => {
    api<ProductRow[]>('/cabinet/products').then(setRows)
  }, [])

  useEffect(load, [load])

  const categories = rows ? [...new Set(rows.map((r) => r.category))] : []

  const submit = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      const created = await api<ProductRow>('/cabinet/products', {
        method: 'POST',
        json: { ...values, expires_at: values.expires_at ? values.expires_at.format('YYYY-MM-DD') : null },
      })
      message.success(`Товар «${created.name}» добавлен в ассортимент`)
      setOpen(false)
      form.resetFields()
      load()
    } catch (e) {
      message.error(e instanceof Error ? e.message : 'Не удалось создать товар')
    } finally {
      setSaving(false)
    }
  }

  if (!rows) return <Spin size="large" style={{ display: 'block', margin: '64px auto' }} />

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography.Title level={4} style={{ margin: 0 }}>
          Ассортимент — {rows.length} товаров, {categories.length} категорий
        </Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
          Добавить товар
        </Button>
      </div>
      <Card size="small">
        <Table<ProductRow>
          rowKey="id"
          dataSource={rows}
          size="small"
          pagination={{ pageSize: 25 }}
          columns={[
            { title: 'Товар', dataIndex: 'name' },
            { title: 'Категория', dataIndex: 'category', render: (c) => <Tag>{c}</Tag> },
            {
              title: 'Цена',
              dataIndex: 'price',
              render: (p, r) => `${p.toLocaleString('ru-RU')} ₽/${r.unit}`,
            },
            { title: 'Остаток', dataIndex: 'stock', render: (s, r) => `${s} ${r.unit}` },
            { title: 'Продажи, шт/день', dataIndex: 'velocity', render: (v) => v.toFixed(1) },
            {
              title: 'Покрытие запаса',
              dataIndex: 'cover_days',
              render: (d) =>
                d == null ? (
                  <Tag>новинка</Tag>
                ) : (
                  <Tag color={d > 45 ? 'orange' : d < 3 ? 'red' : 'green'}>{d} дн.</Tag>
                ),
            },
            {
              title: 'Срок годности',
              dataIndex: 'expires_at',
              render: (e) => (e ? new Date(e).toLocaleDateString('ru-RU') : '—'),
            },
          ]}
        />
      </Card>

      <Modal
        open={open}
        title="Новый товар"
        onCancel={() => setOpen(false)}
        onOk={submit}
        okText="Создать"
        confirmLoading={saving}
        width={640}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            unit: 'шт',
            price: 150,
            cost: 90,
            stock: 20,
            photo_count: 3,
            description_len: 400,
            views_14d: 400,
            cart_14d: 20,
          }}
        >
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
            <Form.Item
              name="name"
              label="Название"
              rules={[{ required: true, message: 'Укажите название' }]}
            >
              <Input placeholder="Простокваша 3,2%" maxLength={128} />
            </Form.Item>
            <Form.Item
              name="category"
              label="Категория"
              rules={[{ required: true, message: 'Выберите или введите категорию' }]}
            >
              <AutoComplete
                options={categories.map((c) => ({ value: c }))}
                placeholder="Молочные напитки"
                filterOption
              />
            </Form.Item>
            <Form.Item name="unit" label="Единица">
              <Select options={UNITS.map((u) => ({ value: u }))} />
            </Form.Item>
            <Form.Item
              name="price"
              label="Цена, ₽"
              rules={[{ required: true, message: 'Укажите цену' }]}
            >
              <InputNumber min={0.5} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="cost" label="Себестоимость, ₽">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="stock" label="Остаток">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="expires_at" label="Срок годности до (необязательно)">
              <DatePicker
                style={{ width: '100%' }}
                disabledDate={(d) => d.isBefore(dayjs(), 'day')}
              />
            </Form.Item>
            <Form.Item name="photo_count" label="Фото в карточке">
              <InputNumber min={0} max={20} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item
              name="description_len"
              label="Описание, знаков"
              tooltip="В прототипе хранится длина описания — по ней правила оценивают карточку"
            >
              <InputNumber min={0} max={5000} style={{ width: '100%' }} />
            </Form.Item>
          </div>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 8, fontSize: 12.5 }}>
            Показатели карточки за 14 дней — симуляция первых дней на маркетплейсе. При 1–2 фото и
            коротком описании помощник сам предложит усилить карточку.
          </Typography.Paragraph>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
            <Form.Item name="views_14d" label="Просмотры за 14 дней">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="cart_14d" label="Добавлений в корзину">
              <InputNumber min={0} style={{ width: '100%' }} />
            </Form.Item>
          </div>
        </Form>
      </Modal>
    </Space>
  )
}
