import { useEffect, useState } from 'react'
import { Alert, Collapse, Descriptions, Modal, Spin, Tag, Typography } from 'antd'
import { api } from '../api'
import type { RulesData } from '../types'

export function HowItWorks({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [data, setData] = useState<RulesData | null>(null)

  useEffect(() => {
    if (open && !data) {
      api<RulesData>('/assistant/rules').then(setData)
    }
  }, [open, data])

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={760}
      title="Как помощник решает, что предложить"
    >
      {!data ? (
        <Spin style={{ display: 'block', margin: '32px auto' }} />
      ) : (
        <>
          <Alert
            type="info"
            showIcon
            message="Каждое утро помощник прогоняет ваши данные через 7 правил. Кандидаты проходят фильтры, ранжируются формулой — и вы видите только топ-3."
            style={{ marginBottom: 16 }}
          />
          <Typography.Title level={5}>Формула приоритета</Typography.Title>
          <Typography.Paragraph code>{data.formula}</Typography.Paragraph>
          <Typography.Title level={5}>Фильтры перед топ-3</Typography.Title>
          <ul style={{ marginTop: 0 }}>
            {data.filters.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
          <Typography.Title level={5}>7 правил-сигналов</Typography.Title>
          <Collapse
            items={data.rules.map((r) => ({
              key: r.key,
              label: r.name,
              children: (
                <Descriptions size="small" column={1} bordered>
                  <Descriptions.Item label="Сигнал">{r.signal}</Descriptions.Item>
                  <Descriptions.Item label="Данные">{r.data}</Descriptions.Item>
                  <Descriptions.Item label="Расчёт эффекта">{r.effect}</Descriptions.Item>
                </Descriptions>
              ),
            }))}
          />
          <Typography.Paragraph type="secondary" style={{ marginTop: 16 }}>
            Отбор действий и расчёт эффекта всегда детерминированы (правила). LLM используется только
            для формулировок — и если она недоступна, помощник работает на шаблонных текстах.
          </Typography.Paragraph>
        </>
      )}
    </Modal>
  )
}

export function RulesTag() {
  return <Tag style={{ color: '#999' }}>7 правил · Score = Эффект × Уверенность × Срочность</Tag>
}
