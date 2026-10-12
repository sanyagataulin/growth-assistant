import { useEffect, useState } from 'react'
import { Badge, Button, Drawer, Space, Tag } from 'antd'
import { ThunderboltOutlined } from '@ant-design/icons'
import { api } from '../api'
import type { ActionItem, TodayData } from '../types'
import { ActionCard } from './ActionCard'
import { ActionModals, type Step } from './ActionModals'

export function AssistantFab() {
  const [data, setData] = useState<TodayData | null>(null)
  const [open, setOpen] = useState(false)
  const [action, setAction] = useState<ActionItem | null>(null)
  const [step, setStep] = useState<Step | null>(null)

  const load = () => api<TodayData>('/assistant/today').then(setData)
  useEffect(() => {
    load().catch(() => {})
  }, [])

  const refresh = () => {
    load().catch(() => {})
    setTimeout(() => window.dispatchEvent(new Event('assistant-updated')), 0)
  }

  return (
    <>
      <div style={{ position: 'fixed', right: 32, bottom: 32, zIndex: 100 }}>
        <Badge count={data?.actions.length ?? 0}>
          <Button
            type="primary"
            size="large"
            shape="circle"
            icon={<ThunderboltOutlined />}
            style={{ width: 56, height: 56, boxShadow: '0 6px 20px rgba(56,158,13,0.45)' }}
            onClick={() => setOpen(true)}
          />
        </Badge>
      </div>
      <Drawer
        title={
          <Space>
            <ThunderboltOutlined style={{ color: '#389e0d' }} />
            <span>3 действия на сегодня</span>
            <Tag>{data?.date}</Tag>
          </Space>
        }
        placement="right"
        width={480}
        open={open}
        onClose={() => setOpen(false)}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {(data?.actions ?? []).map((a) => (
            <ActionCard key={a.id} action={a} compact onOpen={() => {
              setAction(a)
              setStep('details')
            }} />
          ))}
        </Space>
      </Drawer>
      <ActionModals action={action} step={step} onStep={setStep} onChanged={refresh} />
    </>
  )
}
