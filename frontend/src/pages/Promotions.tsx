import { useEffect, useState } from 'react'
import { Card, Space, Spin, Table, Tag, Typography } from 'antd'
import { api } from '../api'
import type { PromotionRow } from '../types'

export function Promotions() {
  const [rows, setRows] = useState<PromotionRow[] | null>(null)

  useEffect(() => {
    api<PromotionRow[]>('/cabinet/promotions').then(setRows)
  }, [])

  if (!rows) return <Spin size="large" style={{ display: 'block', margin: '64px auto' }} />

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={4}>Акции маркетплейса и магазина</Typography.Title>
      <Card size="small">
        <Table<PromotionRow>
          rowKey="id"
          dataSource={rows}
          pagination={false}
          columns={[
            {
              title: 'Акция',
              dataIndex: 'title',
              render: (t, r) => (
                <Space direction="vertical" size={0}>
                  <span style={{ fontWeight: 600 }}>{t}</span>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {r.description}
                  </Typography.Text>
                </Space>
              ),
            },
            {
              title: 'Источник',
              dataIndex: 'scope',
              width: 150,
              render: (s) =>
                s === 'marketplace' ? <Tag color="blue">Маркетплейс</Tag> : <Tag color="green">Магазин</Tag>,
            },
            { title: 'Скидка', dataIndex: 'discount_pct', width: 90, render: (d) => `−${d}%` },
            {
              title: 'Категория',
              dataIndex: 'category',
              width: 180,
              render: (c) => c ?? 'Все товары',
            },
            {
              title: 'Период',
              key: 'period',
              width: 200,
              render: (_, r) =>
                `${new Date(r.starts_at).toLocaleDateString('ru-RU')} — ${new Date(r.ends_at).toLocaleDateString('ru-RU')}`,
            },
            {
              title: 'Статус',
              dataIndex: 'status',
              width: 130,
              render: (s, r) => (
                <Tag color={s === 'Активна' ? 'green' : s === 'Запланирована' ? 'blue' : 'default'}>
                  {s}
                  {s === 'Активна' && r.scope === 'marketplace' && !r.joined ? ' · вы не участвуете' : ''}
                </Tag>
              ),
            },
            {
              title: 'Результат',
              key: 'result',
              width: 160,
              render: (_, r) =>
                r.result_revenue != null
                  ? `${r.result_revenue.toLocaleString('ru-RU')} ₽ (+'${r.result_uplift_pct}%)`
                  : '—',
            },
          ]}
        />
      </Card>
    </Space>
  )
}
