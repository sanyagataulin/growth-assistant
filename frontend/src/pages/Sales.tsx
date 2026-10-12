import { useEffect, useState } from 'react'
import { Card, Col, Row, Space, Spin, Table, Typography } from 'antd'
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from '../api'
import type { SalesData } from '../types'

const PIE_COLORS = ['#389e0d', '#69b34c', '#a3d977', '#2f54eb', '#722ed1', '#fa8c16', '#13c2c2', '#eb2f96']

export function Sales() {
  const [data, setData] = useState<SalesData | null>(null)

  useEffect(() => {
    api<SalesData>('/cabinet/sales?days=30').then(setData)
  }, [])

  if (!data) return <Spin size="large" style={{ display: 'block', margin: '64px auto' }} />

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={4}>Продажи за 30 дней</Typography.Title>
      <Row gutter={16}>
        <Col span={14}>
          <Card size="small" title="Выручка по дням, ₽">
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={data.by_day}>
                <defs>
                  <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#389e0d" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#389e0d" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                <XAxis
                  dataKey="day"
                  tickFormatter={(d) => new Date(d).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })}
                  fontSize={12}
                />
                <YAxis fontSize={12} />
                <Tooltip
                  formatter={(v: any) => [`${Number(v).toLocaleString('ru-RU')} ₽`, 'Выручка']}
                  labelFormatter={(d) => new Date(d).toLocaleDateString('ru-RU')}
                />
                <Area type="monotone" dataKey="revenue" stroke="#389e0d" fill="url(#rev)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={10}>
          <Card size="small" title="Выручка по категориям">
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie data={data.by_category} dataKey="revenue" nameKey="category" innerRadius={55} outerRadius={100}>
                  {data.by_category.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: any) => `${Number(v).toLocaleString('ru-RU')} ₽`} />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>
      <Card size="small" title="Топ-10 товаров по выручке">
        <Table
          rowKey="name"
          size="small"
          dataSource={data.top_products}
          pagination={false}
          columns={[
            { title: 'Товар', dataIndex: 'name' },
            { title: 'Категория', dataIndex: 'category' },
            { title: 'Продано, шт', dataIndex: 'qty', width: 120 },
            {
              title: 'Выручка, ₽',
              dataIndex: 'revenue',
              width: 140,
              render: (v) => v.toLocaleString('ru-RU'),
            },
          ]}
        />
      </Card>
    </Space>
  )
}
