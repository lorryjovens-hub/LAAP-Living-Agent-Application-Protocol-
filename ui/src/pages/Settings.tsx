import { Save } from 'lucide-react'

export default function Settings() {
  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-gray-400 mt-1">Configure LAAP system</p>
      </div>

      <div className="card space-y-6">
        <div>
          <h2 className="text-lg font-semibold mb-4">LLM Configuration</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Provider</label>
              <select className="input">
                <option>OpenAI</option>
                <option>Anthropic</option>
                <option>DeepSeek</option>
                <option>Ollama</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Model</label>
              <input className="input" type="text" placeholder="gpt-4o" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">API Key</label>
              <input className="input" type="password" placeholder="sk-..." />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Temperature</label>
              <input className="input" type="range" min="0" max="2" step="0.1" defaultValue="0.7" />
            </div>
          </div>
        </div>

        <div className="border-t border-gray-700/50 pt-6">
          <h2 className="text-lg font-semibold mb-4">Cognitive Settings</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">RSI Self-Improvement</p>
                <p className="text-sm text-gray-400">Enable recursive self-improvement engine</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" defaultChecked />
                <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-laap-gold"></div>
              </label>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Emotion System</p>
                <p className="text-sm text-gray-400">Enable EG-MRSI emotion gradient</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" defaultChecked />
                <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-laap-gold"></div>
              </label>
            </div>
          </div>
        </div>

        <button className="btn-primary flex items-center gap-2">
          <Save className="w-4 h-4" />
          Save Settings
        </button>
      </div>
    </div>
  )
}
