import { useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Descriptions,
  Input,
  InputNumber,
  Radio,
  Space,
  Tag,
  Typography,
  message,
} from 'antd'
import { api } from '../api'

export function TargetScreen({
  screen,
  params,
  onChanged,
}: {
  screen: string
  params: Record<string, any>
  onChanged?: () => void
}) {
  switch (screen) {
    case 'markdown_form':
      return (
        <Card size="small" title={`Уценка партии: ${params.product_name}`}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Space size="large">
              <span>
                Скидка: <InputNumber defaultValue={params.suggested_discount_pct} min={5} max={70} addonAfter="%" />
              </span>
              <span>
                Цена после уценки:{' '}
                <b>
                  {Math.round(
                    (params.price ?? 0) * (1 - (params.suggested_discount_pct ?? 0) / 100)
                  )}{' '}
                  ₽
                </b>
              </span>
            </Space>
            <Alert
              type="info"
              message={`Под уценку попадёт ~${params.excess} шт из ${params.stock}. Уценённые товары помечаются бейджем «Скорится» и поднимаются в выдаче категории.`}
            />
          </Space>
        </Card>
      )
    case 'card_editor':
      return (
        <Card size="small" title={`Редактор карточки: ${params.product_name}`}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Space>
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  style={{
                    width: 72,
                    height: 72,
                    borderRadius: 8,
                    background: i <= params.photo_count ? '#d9f7be' : '#f5f5f5',
                    border: '1px dashed #bfbfbf',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#999',
                    fontSize: 12,
                  }}
                >
                  {i <= params.photo_count ? 'фото' : '+ фото'}
                </div>
              ))}
            </Space>
            <Input.TextArea
              rows={4}
              defaultValue={
                params.description_len >= 200
                  ? 'Текущее описание продукта (уже достаточно подробное).'
                  : 'Фермерский продукт с пастбищного содержания. Свежая партия, доставка на следующий день. Состав: только натуральные ингредиенты. Хранить в холодильнике до 5 суток.'
              }
            />
            {(params.fixes ?? []).map((f: string) => (
              <Tag key={f} color="orange">
                {f}
              </Tag>
            ))}
          </Space>
        </Card>
      )
    case 'mailing_form':
      return (
        <Card size="small" title="Рассылка постоянным клиентам">
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Descriptions size="small" bordered column={1}>
              <Descriptions.Item label="Получателей">{params.client_count}</Descriptions.Item>
              <Descriptions.Item label="Промокод">{params.suggested_discount_pct}% на следующую покупку</Descriptions.Item>
              {(params.sample_refs ?? []).length > 0 && (
                <Descriptions.Item label="Примеры">(обезличено) {params.sample_refs.join(', ')}</Descriptions.Item>
              )}
            </Descriptions>
            <Input.TextArea
              rows={4}
              defaultValue={`Здравствуйте! Это ферма «Луговое». Мы заметили, что вы давно не заглядывали, — дарим скидку ${params.suggested_discount_pct}% на следующий заказ до конца недели. Свежая партия уже в продаже!`}
            />
            <Alert type="info" message="Отправка — сегодня до 18:00. Доля вернувшихся появится в журнале через 3 дня." />
          </Space>
        </Card>
      )
    case 'promo_join':
      return <PromoJoinScreen params={params} onChanged={onChanged} />
    case 'price_form':
      return (
        <Card size="small" title={`Изменение цены: ${params.product_name}`}>
          <Space direction="vertical" size="middle">
            <Radio.Group defaultValue={params.direction === 'down' ? 'suggest' : 'suggest'}>
              <Radio value="suggest">
                {params.direction === 'down' ? 'Снизить' : 'Поднять'} до{' '}
                <b>{params.suggested_price} ₽</b> (сейчас {params.current_price} ₽, медиана категории{' '}
                {params.median_price} ₽)
              </Radio>
              <Radio value="custom">Своя цена</Radio>
            </Radio.Group>
            <Alert
              type="info"
              message={
                params.direction === 'down'
                  ? 'После изменения конверсия карточки обновится в кабинете через 24 часа.'
                  : 'Небольшое повышение при устойчивом спросе почти не влияет на продажи, но добавляет маржу.'
              }
            />
          </Space>
        </Card>
      )
    case 'restock_form':
      return (
        <Card size="small" title={`Пополнение запаса: ${params.product_name}`}>
          <Descriptions size="small" bordered column={1}>
            <Descriptions.Item label="Остаток">{params.stock} шт</Descriptions.Item>
            <Descriptions.Item label="Скорость продаж">{params.velocity} шт/день</Descriptions.Item>
            <Descriptions.Item label="Рекомендованный заказ">{params.reorder_qty} шт (~2 недели)</Descriptions.Item>
          </Descriptions>
        </Card>
      )
    case 'bundle_form':
      return (
        <Card size="small" title={`Сборка набора: ${params.product_name}`}>
          <Alert
            type="info"
            message={`Запас покрывает ${params.cover_days} дней продаж. Набор из затовара и ходового товара + акция 15% на 5 дней ускорит оборачиваемость.`}
          />
        </Card>
      )
    case 'product_diag':
      return (
        <Card size="small" title={`Диагностика: ${params.product_name}`}>
          <Typography.Text type="secondary">Чек-лист проверки падения продаж:</Typography.Text>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
            {(params.checks ?? []).map((c: string) => (
              <Checkbox key={c}>{c}</Checkbox>
            ))}
          </div>
        </Card>
      )
    default:
      return (
        <Card size="small" title="Выполнение действия">
          <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap' }}>{JSON.stringify(params, null, 2)}</pre>
        </Card>
      )
  }
}

// единственный целевой экран, пишущий в базу
function PromoJoinScreen({ params, onChanged }: { params: Record<string, any>; onChanged?: () => void }) {
  const [joined, setJoined] = useState(false)
  const [busy, setBusy] = useState(false)
  const [selected, setSelected] = useState<string[]>(params.product_names ?? [])

  const doJoin = async () => {
    setBusy(true)
    try {
      await api(`/cabinet/promotions/${params.promo_id}/join`, { method: 'POST' })
      setJoined(true)
      onChanged?.()
      message.success('Вы участвуете в акции — помощник увидит это при следующем расчёте')
    } catch (e) {
      message.error(e instanceof Error ? e.message : 'Не удалось подключиться к акции')
    } finally {
      setBusy(false)
    }
  }

  if (joined) {
    return (
      <Card size="small" title={`Акция маркетплейса: ${params.promo_title}`}>
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Alert
            type="success"
            showIcon
            message={`Вы подключили ${selected.length} товаров к акции «${params.promo_title}»`}
            description="Подключение сохранено в кабинете: вкладка «Акции» покажет ваше участие, а действие «Подключиться» больше не вернётся в топ-3."
          />
          {selected.length > 0 && (
            <Typography.Text type="secondary">Товары в акции: {selected.join(', ')}</Typography.Text>
          )}
        </Space>
      </Card>
    )
  }

  return (
    <Card size="small" title={`Акция маркетплейса: ${params.promo_title}`}>
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Descriptions size="small" bordered column={3}>
          <Descriptions.Item label="Скидка акции">{params.discount_pct}%</Descriptions.Item>
          <Descriptions.Item label="Категория">{params.category}</Descriptions.Item>
          <Descriptions.Item label="Закончится">
            {params.ends_at ? new Date(params.ends_at + 'T00:00:00').toLocaleDateString('ru-RU') : '—'}
          </Descriptions.Item>
        </Descriptions>
        <div>
          <Typography.Text type="secondary">Выберите товары для участия:</Typography.Text>
          <Checkbox.Group
            value={selected}
            onChange={(vals) => setSelected(vals as string[])}
            style={{ display: 'flex', flexDirection: 'column', marginTop: 8, gap: 4 }}
          >
            {(params.product_names ?? []).map((n: string) => (
              <Checkbox key={n} value={n}>
                {n}
              </Checkbox>
            ))}
          </Checkbox.Group>
        </div>
        <Space>
          <Button type="primary" loading={busy} disabled={selected.length === 0} onClick={doJoin}>
            Подключить {selected.length} товаров
          </Button>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            Подключение сохранится в кабинете — помощник увидит его при следующем расчёте
          </Typography.Text>
        </Space>
      </Space>
    </Card>
  )
}
