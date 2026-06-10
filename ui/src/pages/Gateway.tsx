import { MessageSquare, Activity } from 'lucide-react'

const platforms = [
  { name: 'Discord', status: 'connected', messages: '2,341' },
  { name: 'Telegram', status: 'connected', messages: '1,876' },
  { name: 'Slack', status: 'disconnected', messages: '0' },
  { name: 'WeChat', status: 'connected', messages: '4,214' },
  { name: 'DingTalk', status: 'connected', messages: '1,023' },
  { name: 'Feishu', status: 'disconnected', messages: '0' },
]

export default function Gateway() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Gateway</h1>
        <p className="text-gray-400 mt-1">Message platform integrations</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {platforms.map(({ name, status, messages }) => (
          <div key={name} className="card">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-laap-accent/30 rounded-lg">
                  <MessageSquare className="w-5 h-5 text-laap-teal" />
                </div>
                <h3 className="font-semibold">{name}</h3>
              </div>
              <div className={`flex items-center gap-1.5 text-xs ${
                status === 'connected' ? 'text-green-400' : 'text-red-400'
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  status === 'connected' ? 'bg-green-500' : 'bg-red-500'
                }`} />
                {status}
              </div>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-400">
              <div className="flex items-center gap-1">
                <Activity className="w-4 h-4" />
                <span>{messages} messages</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
