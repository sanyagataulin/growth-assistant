import { useState } from 'react'
import { Button, Card, Form, Input, Typography } from 'antd'
import { api } from '../api'
import type { Farmer } from '../types'

export function Login({ onLogin }: { onLogin: (token: string, farmer: Farmer) => void }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (values: { login: string; password: string }) => {
    setLoading(true)
    setError('')
    try {
      const res = await api<{ token: string; farmer: Farmer }>('/auth/login', {
        method: 'POST',
        json: values,
      })
      onLogin(res.token, res.farmer)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка входа')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #f6ffed 0%, #e6f4ff 100%)',
      }}
    >
      <Card style={{ width: 400, boxShadow: '0 8px 30px rgba(0,0,0,0.08)' }}>
        <Typography.Title level={3} style={{ textAlign: 'center', marginBottom: 4 }}>
          🌱 Помощник роста
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ textAlign: 'center' }}>
          Кабинет фермера маркетплейса
        </Typography.Paragraph>
        <Form layout="vertical" onFinish={submit} initialValues={{ login: 'farmer', password: 'farmer123' }}>
          <Form.Item name="login" label="Логин" rules={[{ required: true }]}>
            <Input placeholder="farmer" />
          </Form.Item>
          <Form.Item name="password" label="Пароль" rules={[{ required: true }]}>
            <Input.Password placeholder="••••••••" />
          </Form.Item>
          {error && <Typography.Text type="danger">{error}</Typography.Text>}
          <Button type="primary" htmlType="submit" block loading={loading}>
            Войти
          </Button>
        </Form>
        <Typography.Text type="secondary" style={{ display: 'block', marginTop: 12, fontSize: 12 }}>
          Демо-доступ: farmer / farmer123
        </Typography.Text>
      </Card>
    </div>
  )
}
