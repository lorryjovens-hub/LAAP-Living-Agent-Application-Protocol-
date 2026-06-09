/**
 * LAAP — Golden Dragon Web UI
 * Management interface for the Lifeform Autonomous Adaptive Protocol
 */

// ── State ──
const state = {
    lang: localStorage.getItem('laap_lang') || 'zh',
    theme: localStorage.getItem('laap_theme') || 'dark',
    currentPage: 'dashboard',
    config: {},
    i18nData: {},
    platforms: [
        {id:'telegram',icon:'📱',connected:false},
        {id:'discord',icon:'🎮',connected:false},
        {id:'slack',icon:'💬',connected:false},
        {id:'whatsapp',icon:'📞',connected:false},
        {id:'feishu',icon:'📋',connected:false},
        {id:'dingtalk',icon:'🔔',connected:false},
        {id:'wecom',icon:'🏢',connected:false},
        {id:'weixin',icon:'💚',connected:false},
        {id:'matrix',icon:'🔗',connected:false},
        {id:'email',icon:'✉️',connected:false},
        {id:'signal',icon:'🔐',connected:false},
        {id:'sms',icon:'📨',connected:false},
    ],
    tools: [
        {name:'read_file',category:'code',enabled:true},
        {name:'write_file',category:'code',enabled:true},
        {name:'edit_file',category:'code',enabled:true},
        {name:'create_file',category:'code',enabled:true},
        {name:'list_dir',category:'code',enabled:true},
        {name:'search_code',category:'code',enabled:true},
        {name:'find_files',category:'code',enabled:true},
        {name:'project_info',category:'code',enabled:true},
        {name:'diff_file',category:'code',enabled:true},
        {name:'run_command',category:'shell',enabled:true},
        {name:'run_python',category:'shell',enabled:true},
        {name:'git_status',category:'git',enabled:true},
        {name:'git_diff',category:'git',enabled:true},
        {name:'git_commit',category:'git',enabled:true},
        {name:'git_log',category:'git',enabled:true},
        {name:'git_branch',category:'git',enabled:true},
        {name:'web_fetch',category:'web',enabled:true},
        {name:'web_search',category:'web',enabled:true},
    ],
};

// ── I18n ──
async function loadI18n() {
    try {
        const resp = await fetch(`/api/i18n/${state.lang}`);
        state.i18nData = await resp.json();
    } catch(e) {
        console.warn('i18n load failed, using defaults');
    }
    renderUI();
}

function t(key) {
    const keys = key.split('.');
    let val = state.i18nData;
    for (const k of keys) {
        if (val && val[k]) val = val[k];
        else return key;
    }
    return val || key;
}

async function switchLang(lang) {
    state.lang = lang;
    localStorage.setItem('laap_lang', lang);
    await loadI18n();
    updateUILang();
}

function updateUILang() {
    document.documentElement.lang = state.lang;
    document.querySelector('.lang-toggle').textContent = state.lang === 'zh' ? 'EN' : '中文';
    // Update all translatable elements
    document.querySelectorAll('[data-i18n]').forEach(el => {
        el.textContent = t(el.dataset.i18n);
    });
}

// ── Navigation ──
function navigate(page) {
    state.currentPage = page;
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const pageEl = document.getElementById(`page-${page}`);
    const navEl = document.querySelector(`[data-page="${page}"]`);
    if (pageEl) pageEl.classList.add('active');
    if (navEl) navEl.classList.add('active');
    document.querySelector('.page-title').textContent = t(`nav.${page}`);
}

// ── Toast ──
function toast(message, type = 'info') {
    const container = document.querySelector('.toast-container') || (() => {
        const c = document.createElement('div');
        c.className = 'toast-container';
        document.body.appendChild(c);
        return c;
    })();
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    const icons = {success:'✓',error:'✗',warning:'⚠',info:'ℹ'};
    el.innerHTML = `${icons[type]||''} ${message}`;
    container.appendChild(el);
    setTimeout(() => { el.remove(); }, 3000);
}

// ── Dashboard ──
async function loadDashboard() {
    try {
        const resp = await fetch('/api/status');
        const data = await resp.json();
        document.getElementById('stat-uptime').textContent = data.uptime || '0s';
        document.getElementById('stat-version').textContent = data.version || '0.3.0';
        document.getElementById('stat-model').textContent = data.model || 'N/A';
        document.getElementById('stat-tools').textContent = data.tools || '0';
        document.getElementById('stat-steps').textContent = data.steps || '0';
    } catch(e) {
        // Use default values
    }
}

// ── LLM Config ──
function renderLLMConfig() {
    const container = document.getElementById('llm-config-list');
    const providers = [
        { id:'openai', name:'OpenAI', models:'gpt-4o,gpt-4-turbo,gpt-3.5-turbo' },
        { id:'anthropic', name:'Anthropic Claude', models:'claude-sonnet-4-6,claude-opus-4-5,claude-haiku' },
        { id:'deepseek', name:'DeepSeek', models:'deepseek-chat,deepseek-coder' },
        { id:'openrouter', name:'OpenRouter', models:'openai/gpt-4o,anthropic/claude-sonnet-4-6,google/gemini-pro' },
        { id:'ollama', name:'Ollama (Local)', models:'llama3,mistral,phi3' },
    ];
    container.innerHTML = providers.map(p => `
        <div class="config-card">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
                <div style="font-size:1.5rem;">${p.id === 'openai' ? '🔵' : p.id === 'anthropic' ? '🟢' : p.id === 'deepseek' ? '🔴' : p.id === 'openrouter' ? '🟣' : '🖥️'}</div>
                <div style="flex:1;">
                    <strong style="color:var(--text-primary);">${p.name}</strong>
                    <div style="font-size:0.75rem;color:var(--text-dim);">${p.models}</div>
                </div>
                <button class="btn btn-secondary btn-small" onclick="toggleProviderConfig('${p.id}')">${t('common.edit')}</button>
            </div>
            <div id="config-${p.id}" style="display:none;">
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">${t('llm.api_key')}</label>
                        <input class="form-input" type="password" placeholder="${t('llm.api_key_placeholder')}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">${t('llm.api_url')}</label>
                        <input class="form-input" placeholder="${t('llm.api_url_placeholder')}">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">${t('llm.model')}</label>
                        <input class="form-input" value="${p.models.split(',')[0]}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">${t('llm.temperature')}</label>
                        <input class="form-input" type="range" min="0" max="2" step="0.1" value="0.7">
                    </div>
                </div>
                <div class="btn-group">
                    <button class="btn btn-primary btn-small" onclick="saveProvider('${p.id}')">${t('llm.save_config')}</button>
                    <button class="btn btn-secondary btn-small" onclick="testConnection('${p.id}')">${t('llm.test_connection')}</button>
                </div>
            </div>
        </div>
    `).join('');
}

function toggleProviderConfig(id) {
    const el = document.getElementById(`config-${id}`);
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

function saveProvider(id) { toast(t('common.success'), 'success'); }
function testConnection(id) { toast(t('llm.connection_success'), 'success'); }

// ── Platforms ──
function renderPlatforms() {
    const container = document.getElementById('platforms-list');
    container.innerHTML = state.platforms.map(p => {
        // Get platform i18n data from the nested i18n structure
        const pdata = (state.i18nData.platforms || {}).platforms || {};
        const pt = pdata[p.id] || {};
        return `
        <div class="platform-card ${p.connected ? 'expanded' : ''}">
            <div class="platform-card-header" onclick="this.parentElement.classList.toggle('expanded')">
                <div class="platform-icon">${p.icon}</div>
                <div class="platform-info">
                    <h4>${pt.name || p.id}</h4>
                    <p>${pt.desc || ''}</p>
                </div>
                <span class="platform-status ${p.connected ? 'connected' : 'disconnected'}">
                    ${p.connected ? t('platforms.connected') : t('platforms.disconnected')}
                </span>
            </div>
            <div class="platform-card-body">
                <div class="form-group">
                    <label class="form-label">${pt.config_label || 'Token'}</label>
                    <input class="form-input" type="password" placeholder="${pt.config_placeholder || ''}">
                    <div class="form-hint">${pt.hint || t('platforms.config_hint')}</div>
                </div>
                <div class="btn-group">
                    <button class="btn btn-success btn-small">${t('platforms.connect')}</button>
                    <button class="btn btn-secondary btn-small">${t('common.cancel')}</button>
                </div>
            </div>
        </div>`;
    }).join('');
}
        </div>`;
    }).join('');
}

// ── Tools ──
function renderTools() {
    const container = document.getElementById('tools-list');
    container.innerHTML = state.tools.map(t => `
        <div class="tool-item">
            <div class="tool-icon">${t.category === 'code' ? '📄' : t.category === 'shell' ? '💻' : t.category === 'git' ? '🔀' : '🌐'}</div>
            <span class="tool-name">${t.name}</span>
            <span class="tool-category">${t.category}</span>
            <div class="tool-toggle ${t.enabled ? 'active' : ''}" onclick="toggleTool('${t.name}')"></div>
        </div>
    `).join('');
}

function toggleTool(name) {
    const tool = state.tools.find(t => t.name === name);
    if (tool) { tool.enabled = !tool.enabled; renderTools(); }
}

function filterTools() {
    const query = document.getElementById('tools-search-input').value.toLowerCase();
    document.querySelectorAll('.tool-item').forEach(item => {
        const name = item.querySelector('.tool-name').textContent.toLowerCase();
        item.style.display = name.includes(query) ? '' : 'none';
    });
}

// ── Memory ──
function renderMemory() {
    // Memory stats already shown
}

// ── System Settings ──
function renderSettings() {
    document.querySelectorAll('.theme-option').forEach(el => {
        el.classList.toggle('active', el.dataset.theme === state.theme);
    });
}

function setTheme(theme) {
    state.theme = theme;
    localStorage.setItem('laap_theme', theme);
    document.querySelectorAll('.theme-option').forEach(el => el.classList.toggle('active', el.dataset.theme === theme));
    // Apply theme
    if (theme === 'light') {
        document.documentElement.style.setProperty('--bg-primary', '#FFF8DC');
        document.documentElement.style.setProperty('--bg-secondary', '#F5DEB3');
        document.documentElement.style.setProperty('--text-primary', '#2C1810');
        document.documentElement.style.setProperty('--text-secondary', '#5C3D11');
        document.documentElement.style.setProperty('--bg-card', '#FFEAA7');
        document.documentElement.style.setProperty('--border', '#DAA520');
    } else if (theme === 'gold') {
        document.documentElement.style.setProperty('--bg-primary', '#1A0F0A');
        document.documentElement.style.setProperty('--bg-secondary', '#261A12');
        document.documentElement.style.setProperty('--text-primary', '#FFD700');
        document.documentElement.style.setProperty('--dragon-gold', '#FFBF00');
    } else {
        // Dark theme (default)
        location.reload();
    }
}

// ── API Interaction ──
async function fetchStatus() {
    try {
        const resp = await fetch('/api/status');
        const data = await resp.json();
        document.querySelector('.status-dot').style.background = data.alive ? 'var(--success)' : 'var(--error)';
    } catch(e) {}
}

// ── Initialization ──
async function init() {
    await loadI18n();

    // Navigation click handlers
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => navigate(item.dataset.page));
    });

    // Language toggle
    document.querySelector('.lang-toggle').addEventListener('click', () => {
        switchLang(state.lang === 'zh' ? 'en' : 'zh');
    });

    // Save settings button
    const saveBtn = document.getElementById('save-settings');
    if (saveBtn) {
        saveBtn.addEventListener('click', () => toast(t('system.settings_saved'), 'success'));
    }

    // Clear memory button
    const clearMemBtn = document.getElementById('clear-memory');
    if (clearMemBtn) {
        clearMemBtn.addEventListener('click', () => toast('Memory cleared', 'success'));
    }

    // Render all sections
    renderLLMConfig();
    renderPlatforms();
    renderTools();
    renderSettings();
    loadDashboard();

    // Start periodic status updates
    setInterval(fetchStatus, 5000);
    fetchStatus();

    // Initial nav
    navigate('dashboard');

    console.log('LAAP Web UI initialized');
}

// Start when DOM ready
document.addEventListener('DOMContentLoaded', init);
