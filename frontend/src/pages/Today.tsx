import { useCallback, useEffect, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Col,
  Row,
  Space,
  Spin,
  Statistic,
  Tag,
  Tooltip,
  Typography,
} from 'antd'
import {
  CalendarOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import { api } from '../api'
import type { ActionItem, Overview, TodayData } from '../types'
import { ActionCard } from '../components/ActionCard'
import { ActionModals, type Step } from '../components/ActionModals'
import { HowItWorks } from '../components/HowItWorks'

function fmtDate(iso: string) {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })
}

function localIso(offsetDays: number) {
  const d = new Date(Date.now() + offsetDays * 86400000)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mm}-${dd}`
}

export function Today() {
  const [today, setToday] = useState<TodayData | null>(null)
  const [overview, setOverview] = useState<Overview | null>(null)
  const [dayOffset, setDayOffset] = useState(0)
  const [action, setAction] = useState<ActionItem | null>(null)
  const [step, setStep] = useState<Step | null>(null)
  const [howOpen, setHowOpen] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async (offset: number) => {
    setLoading(true)
    try {
      const iso = localIso(offset)
      const [t, o] = await Promise.all([
        api<TodayData>(`/assistant/today?day=${iso}`),
        api<Overview>('/cabinet/overview'),
      ])
      setToday(t)
      setOverview(o)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load(dayOffset)
  }, [dayOffset, load])

  const refresh = () => load(dayOffset)

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <Row gutter={[16, 16]} align="middle">
        <Col flex="auto">
          <Space align="center" size="middle">
            <Typography.Title level={3} style={{ margin: 0 }}>
              Доброе утро, {today ? 'фермер' : ''}! 👋
            </Typography.Title>
          </Space>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
            Вот три действия с наибольшим эффектом на <b>{today && fmtDate(today.date)}</b>
          </Typography.Paragraph>
        </Col>
        <Col>
          <Space>
            <Space.Compact>
              <Button
                icon={<CalendarOutlined />}
                onClick={() => setDayOffset(dayOffset - 1)}
              >
                − день
              </Button>
              <Button
                disabled={dayOffset === 0}
                onClick={() => setDayOffset(0)}
              >
                Сегодня
              </Button>
              <Button onClick={() => setDayOffset(dayOffset + 1)}>+ день</Button>
            </Space.Compact>
            <Tooltip title="Топ-3 пересчитывается на выбранную дату">
              <QuestionCircleOutlined style={{ color: '#bbb' }} />
            </Tooltip>
            <Button icon={<ReloadOutlined />} onClick={refresh} />
            <Button onClick={() => setHowOpen(true)}>Как помощник решает?</Button>
          </Space>
        </Col>
      </Row>

      {today && (
        <Row gutter={[16, 8]}>
          <Col>
            <Tag color={today.llm.enabled ? 'green' : 'orange'}>
              {today.llm.enabled ? `Формулировки: ${today.llm.model}` : 'Формулировки: шаблоны (нет ключа LLM)'}
            </Tag>
          </Col>
          <Col>
            <Tag>
              Кандидатов от правил: {today.candidates_found} → после фильтров: {today.candidates_passed} → топ-3
            </Tag>
          </Col>
        </Row>
      )}

      <Row gutter={16}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Выручка за 7 дней"
              value={overview?.revenue_7d.toLocaleString('ru-RU')}
              suffix="₽"
            />
            <Typography.Text type={((overview?.revenue_trend ?? 0) >= 0 ? 'success' : 'danger') as any}>
              {(overview?.revenue_trend ?? 0) >= 0 ? '▲' : '▼'} {Math.abs(overview?.revenue_trend ?? 0)}% к прошлой неделе
            </Typography.Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="Заказов за 7 дней" value={overview?.orders_7d} />
            <Typography.Text type="secondary">средний чек {overview?.avg_check.toLocaleString('ru-RU')} ₽</Typography.Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="Постоянных клиентов" value={overview?.repeat_clients} />
            <Typography.Text type="secondary">+{overview?.new_clients_30d} новых за 30 дней</Typography.Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="Эффект помощника"
              value={overview?.assistant_effect.toLocaleString('ru-RU')}
              suffix="₽/нед"
              valueStyle={{ color: '#389e0d' }}
            />
            <Typography.Text type="secondary">от выполненных действий</Typography.Text>
          </Card>
        </Col>
      </Row>

      {loading ? (
        <Spin size="large" style={{ display: 'block', margin: '64px auto' }} />
      ) : (
        <Row gutter={[16, 16]}>
          {(today?.actions ?? []).map((a) => (
            <Col key={a.id} span={8}>
              <ActionCard action={a} onOpen={() => { setAction(a); setStep('details') }} />
            </Col>
          ))}
          {today && today.actions.length === 0 && (
            <Col span={24}>
              <Alert type="success" message="На эту дату значимых действий не нашлось — магазин в порядке." />
            </Col>
          )}
        </Row>
      )}

      <ActionModals action={action} step={step} onStep={setStep} onChanged={refresh} />
      <HowItWorks open={howOpen} onClose={() => setHowOpen(false)} />
    </Space>
  )
}
