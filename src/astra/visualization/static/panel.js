// ASTRA Autonomy Control Panel
const API_BASE = 'http://127.0.0.1:8765/api';

let ws = null;
let currentStatus = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadTriggers();
    loadStatus();
    setupEventListeners();
    setupWebSocket();
    setupSensorControls();
    
    // Auto-refresh every 5 seconds
    setInterval(loadStatus, 5000);
});

// WebSocket connection
function setupWebSocket() {
    ws = new WebSocket('ws://127.0.0.1:8765/ws/graph');
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'autonomy_event') {
            appendEvent(data);
        }
    };
    
    ws.onclose = () => {
        console.log('WebSocket closed, reconnecting...');
        setTimeout(setupWebSocket, 3000);
    };
}

// Event Listeners
function setupEventListeners() {
    document.getElementById('apply').onclick = applySettings;
    document.getElementById('pushSensors').onclick = pushSensors;
    document.getElementById('resetCD').onclick = resetCooldowns;
    document.getElementById('refreshStatus').onclick = loadStatus;
}

// Sensor Controls
function setupSensorControls() {
    const sensors = ['silence', 'backlog', 'creative', 'emotional'];
    sensors.forEach(sensor => {
        const input = document.getElementById(`s_${sensor}`);
        const output = document.getElementById(`o_${sensor}`);
        input.oninput = () => {
            output.textContent = input.value;
        };
    });
    
    // Reset silence button
    const resetBtn = document.getElementById('reset_silence');
    if (resetBtn) {
        resetBtn.onclick = () => {
            document.getElementById('s_silence').value = 0;
            document.getElementById('o_silence').textContent = '0';
        };
    }
}

// Load Triggers
async function loadTriggers() {
    try {
        const resp = await fetch(`${API_BASE}/autonomy/triggers`);
        const triggers = await resp.json();
        
        const container = document.getElementById('triggers');
        container.innerHTML = '';
        
        triggers.forEach(trigger => {
            const card = createTriggerCard(trigger);
            container.appendChild(card);
        });
    } catch (err) {
        console.error('Failed to load triggers:', err);
    }
}

// Create Trigger Card
function createTriggerCard(trigger) {
    const card = document.createElement('div');
    card.className = `trigger-card ${trigger.enabled ? 'active' : 'disabled'}`;
    card.id = `trigger-${trigger.id}`;
    
    const condition = trigger.condition;
    const action = trigger.action;
    
    card.innerHTML = `
        <div class="trigger-header">
            <div class="trigger-title">${condition.name}</div>
            <div class="trigger-priority">P${condition.priority}</div>
        </div>
        <div class="trigger-condition">
            ${condition.sensor_key} ${condition.compare} ${condition.threshold}
        </div>
        <div class="trigger-prompt">"${action.prompt}"</div>
        <div class="trigger-stats">
            <span>🔥 Fired: ${trigger.fire_count || 0}x</span>
            <span>⏱️ Cooldown: ${condition.cooldown_seconds}s</span>
            ${condition.active_modes ? `<span>🎨 Modes: ${condition.active_modes.join(', ')}</span>` : ''}
        </div>
        <div class="trigger-toggle">
            <label class="toggle-label">
                <input type="checkbox" ${trigger.enabled ? 'checked' : ''} onchange="toggleTrigger('${trigger.id}', this.checked)" />
                <span class="toggle-slider"></span>
                <span class="toggle-text">${trigger.enabled ? 'Enabled' : 'Disabled'}</span>
            </label>
        </div>
    `;
    
    return card;
}

// Toggle Trigger
async function toggleTrigger(triggerId, enabled) {
    try {
        await fetch(`${API_BASE}/autonomy/trigger/${triggerId}?enabled=${enabled}`, {
            method: 'PUT'
        });
        loadTriggers();
    } catch (err) {
        console.error('Failed to toggle trigger:', err);
        alert('Failed to toggle trigger');
    }
}

// Apply Settings
async function applySettings() {
    const enabled = document.getElementById('enable').checked;
    const cap = parseInt(document.getElementById('cap').value);
    
    try {
        // Enable/disable autonomy
        await fetch(`${API_BASE}/autonomy/enable?enabled=${enabled}`, {
            method: 'POST'
        });
        
        // Set priority cap
        await fetch(`${API_BASE}/autonomy/priority_cap?cap=${cap}`, {
            method: 'POST'
        });
        
        alert('✅ Settings applied!');
        loadStatus();
    } catch (err) {
        console.error('Failed to apply settings:', err);
        alert('❌ Failed to apply settings');
    }
}

// Push Sensors
async function pushSensors() {
    const sensors = {
        silence_minutes: parseFloat(document.getElementById('s_silence').value),
        tasks_pending: parseFloat(document.getElementById('s_backlog').value),
        creative_intensity: parseFloat(document.getElementById('s_creative').value),
        emotional_intensity: parseFloat(document.getElementById('s_emotional').value)
    };
    
    try {
        await fetch(`${API_BASE}/autonomy/sensors`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sensors })
        });
        
        alert('✅ Sensors updated!');
        loadStatus();
    } catch (err) {
        console.error('Failed to push sensors:', err);
        alert('❌ Failed to update sensors');
    }
}

// Reset Cooldowns
async function resetCooldowns() {
    try {
        await fetch(`${API_BASE}/autonomy/reset_cooldowns`, {
            method: 'POST'
        });
        alert('✅ All cooldowns reset!');
    } catch (err) {
        console.error('Failed to reset cooldowns:', err);
        alert('❌ Failed to reset cooldowns');
    }
}

// Load Status
async function loadStatus() {
    try {
        // Load autonomy status
        const statusResp = await fetch(`${API_BASE}/autonomy/status`);
        currentStatus = await statusResp.json();
        
        document.getElementById('status').textContent = JSON.stringify(currentStatus, null, 2);
        
        // Update master controls
        document.getElementById('enable').checked = currentStatus.enabled;
        
        // Update events
        if (currentStatus.recent_events) {
            const eventsContainer = document.getElementById('events');
            eventsContainer.innerHTML = '';
            currentStatus.recent_events.slice(-10).reverse().forEach(event => {
                const eventDiv = document.createElement('div');
                eventDiv.className = `event-item ${event.type || ''}`;
                eventDiv.innerHTML = `
                    <div>${event.message || event.trigger_name || 'Event'}</div>
                    <div class="event-time">${new Date(event.timestamp || Date.now()).toLocaleTimeString()}</div>
                `;
                eventsContainer.appendChild(eventDiv);
            });
        }
        
        // Load health
        const healthResp = await fetch(`${API_BASE}/system/health`);
        const health = await healthResp.json();
        document.getElementById('health').textContent = JSON.stringify(health, null, 2);
        
    } catch (err) {
        console.error('Failed to load status:', err);
    }
}

// Append Event
function appendEvent(event) {
    const eventsContainer = document.getElementById('events');
    const eventDiv = document.createElement('div');
    eventDiv.className = 'event-item fired';
    eventDiv.innerHTML = `
        <div>🔥 Trigger Fired: ${event.trigger_name}</div>
        <div class="event-time">${new Date().toLocaleTimeString()}</div>
    `;
    eventsContainer.insertBefore(eventDiv, eventsContainer.firstChild);
    
    // Keep only last 20 events
    while (eventsContainer.children.length > 20) {
        eventsContainer.removeChild(eventsContainer.lastChild);
    }
}
