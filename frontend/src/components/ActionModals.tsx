import { useState } from 'react'
import {
  Alert,
  Button,
  Descriptions,
  Modal,
  Progress,
  Radio,
  Space,
  Steps,
  Tag,
  Typography,
  message,
} from 'antd'
import { api } from '../api'
import { REJECT_REASONS, TYPE_META, URGENCY_LABEL, type ActionItem } from '../types'
import { TargetScreen } from './TargetScreens'

export type Step = 'details' | 'confirm' | 'target' | 'reject'

interface Props {
  action: ActionItem | null
  step: Step | null
  onStep: (step: Step | null) => void
  onChanged: () => void
}

export function ActionModals({ action, step, onStep, onChanged }: Props) {
  const [rejectReason, setRejectReason] = useState<string>(REJECT_REASONS[0])
  const [busy, setBusy] = useState(false)
  const [target, setTarget] = useState<{ key: string; title: string; params: any } | null>(null)

  if (!action || !step) return null
  const meta = TYPE_META[action.type]

  const doConfirm = async () => {
    setBusy(true)
    try {
      const res = await api<{
        target_screen: { key: string; title: string; params: any }
      }>(`/assistant/${action.id}/confirm`, { method: 'POST' })
      setTarget(res.target_screen)
      onStep('target')
      onChanged()
    } catch (e) {
      message.error(e instanceof Error ? e.message : 'Ошибка')
    } finally {
      setBusy(false)
    }
  }

  const doReject = async () => {
    setBusy(true)
    try {
      await api(`/assistant/${action.id}/reject`, {
        method: 'POST',
        json: { reason: rejectReason },
      })
      message.info('Действие отклонено — не вернётся в топ-3 в течение 14 дней')
      onStep(null)
      onChanged()
    } catch (e) {
      message.error(e instanceof Error ? e.message : 'Ошибка')
    } finally {
      setBusy(false)
    }
  }

  const currentStep = step === 'details' ? 0 : step === 'confirm' ? 1 : 2

  return (
    <>
      <Modal
        open={step === 'details'}
        onCancel={() => onStep(null)}
        width={720}
        footer={
          action.status === 'proposed'
            ? [
                <Button key="reject" onClick={() => onStep('reject')}>
                  Отклонить
                </Button>,
                <Button key="run" type="primary" onClick={() => onStep('confirm')}>
                  Выполнить…
                </Button>,
              ]
            : [
                <Button key="close" type="primary" onClick={() => onStep(null)}>
                  Закрыть
                </Button>,
              ]
        }
        title={
          <Space>
            <Tag color={meta?.color}>{meta?.name ?? action.type}</Tag>
            <span>Действие #{action.id}</span>
          </Space>
        }
      >
        <Typography.Title level={4} style={{ marginTop: 8 }}>
          {action.title}
        </Typography.Title>
        <Typography.Paragraph type="secondary">{action.why}</Typography.Paragraph>

        <Steps
          size="small"
          items={[{ title: 'Сигнал и причина' }, { title: 'Подтверждение' }, { title: 'Выполнение' }]}
          current={currentStep}
          style={{ margin: '16px 0' }}
        />

        <Typography.Text type="secondary">Что мы видим в данных:</Typography.Text>
        <Descriptions size="small" bordered column={1} style={{ margin: '8px 0 16px' }}>
          {Object.entries(action.facts).map(([k, v]) => (
            <Descriptions.Item key={k} label={k}>
              {String(v)}
            </Descriptions.Item>
          ))}
        </Descriptions>

        <Typography.Text type="secondary">Ожидаемый эффект:</Typography.Text>
        <div style={{ display: 'flex', gap: 24, alignItems: 'center', margin: '8px 0 16px' }}>
          <div>
            <div style={{ fontSize: 28, fontWeight: 700, color: '#389e0d' }}>
              +{action.effect_weekly.toLocaleString('ru-RU')} ₽
            </div>
            <div style={{ color: '#999' }}>в неделю</div>
          </div>
          <div style={{ width: 200 }}>
            <div>Уверенность</div>
            <Progress percent={Math.round(action.confidence * 100)} size="small" />
          </div>
          <div>
            <div>Срочность</div>
            <Tag color={URGENCY_LABEL[action.urgency]?.color} style={{ marginTop: 4 }}>
              {action.urgency}/3 — {URGENCY_LABEL[action.urgency]?.label}
            </Tag>
          </div>
        </div>
        <Typography.Paragraph type="secondary" style={{ fontSize: 13 }}>
          {action.effect_note} Приоритет (score) = эффект × уверенность × срочность ={' '}
          <b>{action.score.toLocaleString('ru-RU')}</b>.
        </Typography.Paragraph>

        <Typography.Text type="secondary">План выполнения:</Typography.Text>
        <ol style={{ margin: '8px 0 0', paddingLeft: 20 }}>
          {action.plan.map((p, i) => (
            <li key={i} style={{ marginBottom: 4 }}>
              {p}
            </li>
          ))}
        </ol>
        <div style={{ marginTop: 12, color: '#bbb', fontSize: 12 }}>
          Формулировки: {action.texts_source === 'llm' ? 'сгенерированы LLM' : 'шаблон (LLM недоступен)'} ·
          Помощник не выполнит действие без вашего подтверждения
        </div>
      </Modal>

      <Modal
        open={step === 'confirm'}
        title="Подтвердите действие"
        onCancel={() => onStep('details')}
        width={640}
        footer={[
          <Button key="back" onClick={() => onStep('details')}>
            Вернуться
          </Button>,
          <Button key="ok" type="primary" loading={busy} onClick={doConfirm}>
            Подтверждаю, выполнить
          </Button>,
        ]}
      >
        <Alert
          type="warning"
          showIcon
          message="Помощник ничего не делает сам: действие выполнится только после вашего подтверждения."
          style={{ marginBottom: 16 }}
        />
        <Typography.Paragraph>
          <b>{action.title}</b>
        </Typography.Paragraph>
        <Typography.Text type="secondary">Что произойдёт:</Typography.Text>
        <Descriptions size="small" bordered column={1} style={{ marginTop: 8 }}>
          {confirmParams(action).map(([k, v]) => (
            <Descriptions.Item key={k} label={k}>
              {v}
            </Descriptions.Item>
          ))}
          <Descriptions.Item label="Ожидаемый эффект">
            +{action.effect_weekly.toLocaleString('ru-RU')} ₽/нед
          </Descriptions.Item>
        </Descriptions>
      </Modal>

      <Modal
        open={step === 'target'}
        title={`Переход к выполнению: ${target?.title ?? ''}`}
        onCancel={() => {
          setTarget(null)
          onStep(null)
        }}
        width={720}
        footer={[
          <Button
            key="done"
            type="primary"
            onClick={() => {
              setTarget(null)
              onStep(null)
              message.success('Действие выполнено — результат появится в журнале')
            }}
          >
            Готово
          </Button>,
        ]}
      >
        <Alert
          type="success"
          showIcon
          message="Действие подтверждено. Ниже — экран маркетплейса, куда перешёл фермер (прототип)."
          style={{ marginBottom: 16 }}
        />
        {target && <TargetScreen screen={target.key} params={target.params} onChanged={onChanged} />}
      </Modal>

      <Modal
        open={step === 'reject'}
        title="Почему отклоняете действие?"
        onCancel={() => onStep(null)}
        footer={[
          <Button key="back" onClick={() => onStep(null)}>
            Не отклонять
          </Button>,
          <Button key="ok" danger type="primary" loading={busy} onClick={doReject}>
            Отклонить
          </Button>,
        ]}
      >
        <Typography.Paragraph type="secondary">
          Причина помогает помощнику не приставать с нерелевантными советами: действие исчезнет из
          топ-3 на 14 дней.
        </Typography.Paragraph>
        <Radio.Group
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
          style={{ display: 'flex', flexDirection: 'column', gap: 8 }}
        >
          {REJECT_REASONS.map((r) => (
            <Radio key={r} value={r}>
              {r}
            </Radio>
          ))}
        </Radio.Group>
      </Modal>
    </>
  )
}

function confirmParams(action: ActionItem): [string, string][] {
  const p = action.payload
  switch (p.screen) {
    case 'markdown_form':
      return [
        ['Товар', p.product_name],
        ['Скидка', `${p.suggested_discount_pct}%`],
        ['Единиц под уценкой', `~${p.excess} из ${p.stock}`],
        ['Срок', `до ${p.days_left} дн.`],
      ]
    case 'card_editor':
      return [
        ['Карточка', p.product_name],
        ['Изменения', 'добавить фото, расширить описание'],
      ]
    case 'mailing_form':
      return [
        ['Сегмент', `Постоянные клиенты без покупок (${p.client_count} чел.)`],
        ['Промокод', `${p.suggested_discount_pct}% на следующую покупку`],
      ]
    case 'promo_join':
      return [
        ['Акция', p.promo_title],
        ['Скидка', `${p.discount_pct}%`],
        ['Товаров подключается', String(p.product_ids?.length ?? 0)],
      ]
    case 'price_form':
      return [
        ['Товар', p.product_name],
        ['Текущая цена', `${p.current_price} ₽`],
        ['Новая цена', `${p.suggested_price} ₽`],
      ]
    case 'restock_form':
      return [['Товар', p.product_name], ['Заказ', `${p.reorder_qty} ${p.velocity > 0 ? 'шт (~2 недели)' : ''}`]]
    case 'bundle_form':
      return [['Товар', p.product_name], ['Механика', 'набор с ходовым товаром + акция 15%']]
    case 'product_diag':
      return [['Товар', p.product_name], ['Падение продаж', `${p.drop_pct}%`]]
    default:
      return Object.entries(p).slice(0, 4).map(([k, v]) => [k, String(v)])
  }
}
