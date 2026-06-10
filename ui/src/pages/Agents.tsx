import { Bot, Plus, MoreVertical } from 'lucide-react'

const agents = [
  { name: 'Alpha', type: 'LifelikeAgent', status: 'active', needs: '0.82', confidence: '0.91' },
  { name: 'Beta', type: 'CodexAgent', status: 'active', needs: '0.74', confidence: '0.85' },
  { name: 'Gamma', type: 'LifelikeAgent', status: 'idle', needs: '0.65', confidence: '0.72' },
]

export default function Agents() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Agents</h1>
          <p className="text-gray-400 mt-1">Manage your agent swarm</p>
        </div>
        <button className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          New Agent
        </button>
      </div>

      <div className="grid gap-4">
        {agents.map((agent) => (
          <div key={agent.name} className="card flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-laap-accent/30 rounded-lg">
                <Bot className="w-6 h-6 text-laap-teal" />
              </div>
              <div>
                <h3 className="font-semibold">{agent.name}</h3>
                <p className="text-sm text-gray-400">{agent.type}</p>
              </div>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-right">
                <p className="text-xs text-gray-500">Needs</p>
                <p className="font-mono text-sm">{agent.needs}</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-500">Confidence</p>
                <p className="font-mono text-sm">{agent.confidence}</p>
              </div>
              <div className={`px-2 py-1 rounded text-xs font-medium ${
                agent.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
              }`}>
                {agent.status}
              </div>
              <button className="p-1 hover:bg-gray-700 rounded">
                <MoreVertical className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
