import { Button, Card, Progress, Space, Tag, Tooltip, Typography } from 'antd'
import {
  ArrowRightOutlined,
  CloseOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import { TYPE_META, URGENCY_LABEL, type ActionItem } from '../types'

interface Props {
  action: ActionItem
  compact?: boolean
  onOpen: () => void
}

export function ActionCard({ action, compact, onOpen }: Props) {
  const meta = TYPE_META[action.type]
  const done = action.status !== 'proposed'

  return (
    <Card
      size={compact ? 'small' : 'default'}
      style={done ? { opacity: 0.55 } : undefined}
      title={
        <Space size={8} wrap>
          <Tag color={meta?.color}>{meta?.name ?? action.type}</Tag>
          <Tag color={URGENCY_LABEL[action.urgency]?.color}>
            {URGENCY_LABEL[action.urgency]?.label}
          </Tag>
          {done && (
            <Tag color={action.status === 'completed' ? 'green' : 'default'}>
              {action.status === 'completed' ? 'Выполнено' : 'Отклонено'}
            </Tag>
          )}
        </Space>
      }
      actions={
        done
          ? undefined
          : [
              <Button
                key="run"
                type="primary"
                icon={<ArrowRightOutlined />}
                onClick={onOpen}
              >
                Выполнить…
              </Button>,
              <Tooltip key="info" title="Подробнее: факты, расчёт эффекта, план">
                <Button icon={<InfoCircleOutlined />} onClick={onOpen} />
              </Tooltip>,
              <Button
                key="close"
                type="text"
                icon={<CloseOutlined />}
                onClick={onOpen}
                aria-label="Отклонить"
              />,
            ]
      }
    >
      <Typography.Paragraph strong style={{ marginBottom: 4 }}>
        {action.title}
      </Typography.Paragraph>
      <Typography.Paragraph type="secondary" style={{ fontSize: 13, marginBottom: 8 }}>
        {action.why}
      </Typography.Paragraph>
      <Space size="large" wrap>
        <div>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            Ожидаемый эффект
          </Typography.Text>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#389e0d' }}>
            +{action.effect_weekly.toLocaleString('ru-RU')} ₽/нед
          </div>
        </div>
        <div style={{ width: 120 }}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            Уверенность {Math.round(action.confidence * 100)}%
          </Typography.Text>
          <Progress
            percent={Math.round(action.confidence * 100)}
            size="small"
            showInfo={false}
            strokeColor="#389e0d"
          />
        </div>
        <div>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            Приоритет
          </Typography.Text>
          <div style={{ fontWeight: 600 }}>{action.score.toLocaleString('ru-RU')}</div>
        </div>
      </Space>
    </Card>
  )
}
