import { useEffect, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useAuthStore } from '@/stores/auth-store'
import { api, type LandSupply } from '@/services/api'
import HangzhouMap from '@/components/map/hangzhou-map'
import LandSupplyCard from '@/components/land-supply/land-supply-card'
import AgentChat from '@/components/agent/agent-chat'
import {
  Globe,
  LogOut,
  User,
  Bot,
  Building2,
  Filter,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
} from 'lucide-react'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { user, logout, token } = useAuthStore()
  const [landSupplies, setLandSupplies] = useState<LandSupply[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [districtFilter, setDistrictFilter] = useState<string>('')

  useEffect(() => {
    if (!token) {
      navigate({ to: '/login' })
      return
    }
    loadData()
  }, [token, districtFilter])

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await api.getLandSupplies({
        district: districtFilter || undefined,
        page: 1,
        pageSize: 50,
      })
      setLandSupplies(res.items)
    } catch (err) {
      console.error('Failed to load land supplies', err)
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    logout()
    navigate({ to: '/login' })
  }

  const districts = ['上城区', '拱墅区', '西湖区', '滨江区', '萧山区', '余杭区', '临平区', '钱塘区', '富阳区', '临安区']

  return (
    <div className="h-screen w-screen flex flex-col bg-slate-100 overflow-hidden">
      {/* Top Navigation */}
      <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-4 shrink-0 z-20">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-cyan-500 flex items-center justify-center">
            <Globe className="w-4 h-4 text-white" />
          </div>
          <div className="flex items-center gap-2">
            <LayoutDashboard className="w-4 h-4 text-slate-400" />
            <h1 className="font-semibold text-slate-800 text-sm tracking-wide">
              浙江省空间变化智能监测平台
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 rounded-lg border border-slate-200">
            <User className="w-4 h-4 text-slate-400" />
            <span className="text-sm text-slate-700">{user?.realName}</span>
            <span className="text-xs px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
              {user?.role}
            </span>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            退出
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <div
          className={`relative bg-white border-r border-slate-200 flex flex-col transition-all duration-300 ${
            sidebarOpen ? 'w-[360px]' : 'w-0'
          }`}
        >
          {sidebarOpen && (
            <>
              {/* Sidebar Header */}
              <div className="p-4 border-b border-slate-100">
                <div className="flex items-center gap-2 mb-3">
                  <Building2 className="w-4 h-4 text-blue-600" />
                  <h2 className="font-semibold text-slate-800 text-sm">土地供应信息</h2>
                  <span className="text-xs text-slate-400 ml-auto">
                    共 {landSupplies.length} 条
                  </span>
                </div>

                {/* District Filter */}
                <div className="flex items-center gap-2">
                  <Filter className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <select
                    value={districtFilter}
                    onChange={(e) => setDistrictFilter(e.target.value)}
                    className="flex-1 text-xs bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                  >
                    <option value="">全部行政区</option>
                    {districts.map((d) => (
                      <option key={d} value={d}>
                        {d}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Cards List */}
              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                {loading ? (
                  <div className="flex items-center justify-center py-10">
                    <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                  </div>
                ) : landSupplies.length === 0 ? (
                  <div className="text-center py-10 text-slate-400 text-sm">
                    暂无数据
                  </div>
                ) : (
                  landSupplies.map((item) => (
                    <LandSupplyCard
                      key={item.id}
                      data={item}
                      isSelected={selectedId === item.id}
                      onClick={() => setSelectedId(item.id)}
                    />
                  ))
                )}
              </div>
            </>
          )}

          {/* Toggle Button */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-12 bg-white border border-slate-200 rounded-r-lg flex items-center justify-center shadow-sm hover:bg-slate-50 transition-colors z-10"
          >
            {sidebarOpen ? (
              <ChevronLeft className="w-3 h-3 text-slate-500" />
            ) : (
              <ChevronRight className="w-3 h-3 text-slate-500" />
            )}
          </button>
        </div>

        {/* Map Area */}
        <div className="flex-1 relative">
          <HangzhouMap
            landSupplies={landSupplies}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />

          {/* Map Overlay Info */}
          <div className="absolute top-4 left-4 bg-white/90 backdrop-blur-sm rounded-xl px-4 py-3 shadow-lg border border-slate-200 z-[1000]">
            <h3 className="text-sm font-semibold text-slate-800">杭州市土地供应分布</h3>
            <p className="text-xs text-slate-500 mt-1">
              实时展示杭州市各区土地供应地块位置及交易状态
            </p>
          </div>
        </div>
      </div>

      {/* Agent Floating Button */}
      {!chatOpen && (
        <button
          onClick={() => setChatOpen(true)}
          className="fixed bottom-6 right-6 z-[9998] w-14 h-14 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white rounded-full shadow-xl shadow-blue-500/30 flex items-center justify-center transition-all duration-300 hover:scale-110 group"
        >
          <Bot className="w-6 h-6 group-hover:animate-bounce" />
          <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full border-2 border-white" />
        </button>
      )}

      {/* Agent Chat Window */}
      <AgentChat open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  )
}
