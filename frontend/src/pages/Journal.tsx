import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Col, message, Row, Space, Spin, Statistic, Table, Tag, Typography } from 'antd'
import { api } from '../api'
import { REJECT_REASONS, TYPE_META, type JournalData } from '../types'

export function Journal() {
  const [data, setData] = useState<JournalData | null>(null)

  const load = useCallback(() => {
    api<JournalData>('/assistant/journal').then(setData)
  }, [])

  useEffect(load, [load])

  const sendFeedback = async (id: number, feedback: 'useful' | 'not_useful') => {
    await api(`/assistant/${id}/feedback`, { method: 'POST', json: { feedback } })
    message.success(feedback === 'useful' ? 'Спасибо, учтём' : 'Поняли, станем точнее')
    load()
  }

  if (!data) return <Spin size="large" style={{ display: 'block', margin: '64px auto' }} />
  const m = data.metrics

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Typography.Title level={4}>Журнал действий и метрики</Typography.Title>
      <Row gutter={16}>
        <Col span={4}>
          <Card size="small"><Statistic title="Предложено" value={m.proposed} /></Card>
        </Col>
        <Col span={4}>
          <Card size="small"><Statistic title="Выполнено" value={m.completed} valueStyle={{ color: '#389e0d' }} /></Card>
        </Col>
        <Col span={4}>
          <Card size="small"><Statistic title="Отклонено" value={m.rejected} /></Card>
        </Col>
        <Col span={4}>
          <Card size="small"><Statistic title="Принимаемость" value={m.accepted_rate} suffix="%" /></Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="Эффект выполненных"
              value={m.completed_effect_weekly.toLocaleString('ru-RU')}
              suffix="₽/нед"
              valueStyle={{ color: '#389e0d' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small"><Statistic title="«Полезно» 👍" value={m.useful_votes} /></Card>
        </Col>
      </Row>
      <Card size="small">
        <Table
          rowKey="id"
          size="small"
          dataSource={data.actions}
          pagination={{ pageSize: 15 }}
          columns={[
            {
              title: 'Дата',
              dataIndex: 'day',
              width: 100,
              render: (d) => new Date(d).toLocaleDateString('ru-RU'),
            },
            {
              title: 'Тип',
              dataIndex: 'type',
              width: 160,
              render: (t) => <Tag color={TYPE_META[t]?.color}>{TYPE_META[t]?.name ?? t}</Tag>,
            },
            { title: 'Действие', dataIndex: 'title' },
            {
              title: 'Эффект',
              dataIndex: 'effect_weekly',
              width: 120,
              render: (v) => `+${v.toLocaleString('ru-RU')} ₽/нед`,
            },
            {
              title: 'Статус',
              dataIndex: 'status_name',
              width: 120,
              render: (s, r) => (
                <Tag color={r.status === 'completed' ? 'green' : r.status === 'rejected' ? 'default' : 'blue'}>
                  {s}
                </Tag>
              ),
            },
            {
              title: 'Причина отклонения',
              dataIndex: 'rejection_reason',
              width: 200,
              render: (r) => r ?? '—',
            },
            {
              title: 'Оценка',
              key: 'feedback',
              width: 170,
              render: (_, r) => (
                <Space>
                  <Button
                    size="small"
                    type={r.feedback === 'useful' ? 'primary' : 'default'}
                    onClick={() => sendFeedback(r.id, 'useful')}
                  >
                    👍
                  </Button>
                  <Button
                    size="small"
                    type={r.feedback === 'not_useful' ? 'primary' : 'default'}
                    danger={r.feedback === 'not_useful'}
                    onClick={() => sendFeedback(r.id, 'not_useful')}
                  >
                    👎
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>
      <Typography.Text type="secondary">
        Отклонённые действия ({REJECT_REASONS.join(', ').toLowerCase()} — типичные причины) не
        возвращаются в топ-3 в течение 14 дней. Ожидаемый эффект выполненных действий сравнивается с
        фактическим в отчёте недели.
      </Typography.Text>
    </Space>
  )
}
