import { Activity, Bot, MessageSquare, Cpu } from 'lucide-react'

const stats = [
  { label: 'Active Agents', value: '3', icon: Bot, change: '+1' },
  { label: 'Tasks Completed', value: '1,247', icon: Activity, change: '+12%' },
  { label: 'Messages', value: '8,431', icon: MessageSquare, change: '+5%' },
  { label: 'Uptime', value: '99.9%', icon: Cpu, change: '99.9%' },
]

const recentActivity = [
  { action: 'Agent "Alpha" completed code review', time: '2m ago', status: 'success' },
  { action: 'Gateway: Discord message processed', time: '5m ago', status: 'success' },
  { action: 'RSI evolution cycle completed', time: '15m ago', status: 'info' },
  { action: 'Memory consolidation triggered', time: '1h ago', status: 'info' },
]

export default function Dashboard() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-gray-400 mt-1">LAAP System Overview</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map(({ label, value, icon: Icon, change }) => (
          <div key={label} className="card">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-gray-400 text-sm">{label}</p>
                <p className="text-2xl font-bold mt-1">{value}</p>
              </div>
              <div className="p-2 bg-laap-accent/30 rounded-lg">
                <Icon className="w-5 h-5 text-laap-teal" />
              </div>
            </div>
            <div className="mt-4 text-xs text-green-400">{change} from last week</div>
          </div>
        ))}
      </div>

      <div className="card">
        <h2 className="text-lg font-semibold mb-4">Recent Activity</h2>
        <div className="space-y-3">
          {recentActivity.map(({ action, time, status }) => (
            <div key={action} className="flex items-center justify-between py-2 border-b border-gray-700/30 last:border-0">
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${
                  status === 'success' ? 'bg-green-500' : 'bg-blue-500'
                }`} />
                <span className="text-sm">{action}</span>
              </div>
              <span className="text-xs text-gray-500">{time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
