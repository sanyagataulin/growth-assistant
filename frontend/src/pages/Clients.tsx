import { useEffect, useState } from 'react'
import { Alert, Card, Col, Row, Space, Spin, Statistic, Table, Typography } from 'antd'
import { api } from '../api'
import type { ClientsData } from '../types'

export function Clients() {
  const [data, setData] = useState<ClientsData | null>(null)

  useEffect(() => {
    api<ClientsData>('/cabinet/clients').then(setData)
  }, [])

  if (!data) return <Spin size="large" style={{ display: 'block', margin: '64px auto' }} />

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={4}>Клиентская база (обезличенные данные)</Typography.Title>
      <Row gutter={16}>
        {data.segments.map((s) => (
          <Col key={s.key} span={8}>
            <Card size="small">
              <Statistic title={s.name} value={s.count} suffix="клиентов" />
              <Typography.Text type="secondary">
                суммарно {Math.round(s.spent).toLocaleString('ru-RU')} ₽
              </Typography.Text>
            </Card>
          </Col>
        ))}
      </Row>
      {data.lapsed_count > 0 && (
        <Alert
          type="warning"
          showIcon
          message={`Внимание: ${data.lapsed_count} постоянных клиентов не покупали в среднем ${data.lapsed_avg_silence} дней — помощник предложит вернуть их рассылкой с промокодом`}
        />
      )}
      <Card size="small" title="Топ клиентов по расходам">
        <Table
          rowKey="ext_ref"
          size="small"
          dataSource={data.top}
          pagination={false}
          columns={[
            { title: 'Клиент', dataIndex: 'ext_ref' },
            { title: 'Сегмент', dataIndex: 'segment' },
            { title: 'Заказов', dataIndex: 'orders', width: 100 },
            { title: 'Расходы, ₽', dataIndex: 'spent', width: 130, render: (v) => v.toLocaleString('ru-RU') },
            {
              title: 'Последний заказ',
              dataIndex: 'last_order',
              width: 150,
              render: (d) => new Date(d).toLocaleDateString('ru-RU'),
            },
          ]}
        />
      </Card>
    </Space>
  )
}
