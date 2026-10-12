import { useEffect, useState } from 'react'
import { Layout as AntLayout, Menu } from 'antd'
import {
  AppstoreOutlined,
  DashboardOutlined,
  FileImageOutlined,
  GiftOutlined,
  LogoutOutlined,
  TagsOutlined,
  TeamOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { api, getToken, setToken } from './api'
import type { Farmer } from './types'
import { Login } from './pages/Login'
import { Today } from './pages/Today'
import { Products } from './pages/Products'
import { Cards } from './pages/Cards'
import { Sales } from './pages/Sales'
import { Promotions } from './pages/Promotions'
import { Clients } from './pages/Clients'
import { Journal } from './pages/Journal'
import { AssistantFab } from './components/AssistantFab'

const { Header, Sider, Content } = AntLayout

export type PageKey =
  | 'today'
  | 'products'
  | 'cards'
  | 'sales'
  | 'promotions'
  | 'clients'
  | 'journal'

export default function App() {
  const [farmer, setFarmer] = useState<Farmer | null>(null)
  const [checking, setChecking] = useState(!!getToken())
  const [page, setPage] = useState<PageKey>('today')

  useEffect(() => {
    if (!getToken()) return
    api<Farmer>('/auth/me')
      .then(setFarmer)
      .catch(() => setToken(null))
      .finally(() => setChecking(false))
  }, [])

  if (checking) return null

  if (!farmer) {
    return (
      <Login
        onLogin={(token, f) => {
          setToken(token)
          setFarmer(f)
        }}
      />
    )
  }

  const menuItems = [
    { key: 'today', icon: <ThunderboltOutlined />, label: 'Сегодня' },
    { key: 'products', icon: <AppstoreOutlined />, label: 'Ассортимент' },
    { key: 'cards', icon: <FileImageOutlined />, label: 'Карточки товаров' },
    { key: 'sales', icon: <DashboardOutlined />, label: 'Продажи' },
    { key: 'promotions', icon: <GiftOutlined />, label: 'Акции' },
    { key: 'clients', icon: <TeamOutlined />, label: 'Клиенты' },
    { key: 'journal', icon: <TagsOutlined />, label: 'Журнал действий' },
  ]

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={220}>
        <div
          style={{
            color: '#fff',
            fontWeight: 700,
            fontSize: 17,
            padding: '18px 16px',
            whiteSpace: 'nowrap',
          }}
        >
          🌱 Помощник роста
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[page]}
          items={menuItems}
          onClick={(e) => setPage(e.key as PageKey)}
        />
      </Sider>
      <AntLayout>
        <Header
          style={{
            background: '#fff',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            paddingInline: 24,
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <div>
            <span style={{ fontSize: 16, fontWeight: 600 }}>{farmer.shop_name}</span>
            <span style={{ color: '#999', marginLeft: 12 }}>{farmer.region}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ color: '#666' }}>{farmer.full_name}</span>
            <a
              onClick={() => {
                setToken(null)
                setFarmer(null)
              }}
            >
              <LogoutOutlined /> Выйти
            </a>
          </div>
        </Header>
        <Content style={{ padding: 24, background: '#f5f6f8' }}>
          {page === 'today' && <Today />}
          {page === 'products' && <Products />}
          {page === 'cards' && <Cards />}
          {page === 'sales' && <Sales />}
          {page === 'promotions' && <Promotions />}
          {page === 'clients' && <Clients />}
          {page === 'journal' && <Journal />}
          {page !== 'today' && <AssistantFab />}
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
