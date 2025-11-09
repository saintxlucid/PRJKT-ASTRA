# Phase 13: Operator Console GUI - Implementation Plan

**Timeline:** 4-5 weeks  
**Priority:** MEDIUM  
**Dependencies:** Phases 1-12 complete  
**Status:** READY (after Phase 12)

---

## 🎯 Phase 13 Overview

Operator Console GUI is the **visual interface** for monitoring, controlling, and interacting with ASTRA-OS. Built with PyQt6, it provides real-time dashboards, consent modals, threat visualization, and memory exploration.

### Success Criteria
- ✅ 6 main views (Home, Sentinel, Autonomy, Memory, Radar, Logs)
- ✅ Real-time metrics via Event Bus
- ✅ Rich consent modals with previews
- ✅ Safe word detection
- ✅ Dark/light theme support
- ✅ System tray integration
- ✅ Hotkeys and shortcuts
- ✅ 1000+ lines of code

---

## 🎨 Architecture

```
Operator Console
├─ Main Window
│  ├─ Menu Bar
│  ├─ Tab Widget
│  │  ├─ Home Tab
│  │  ├─ Sentinel Tab
│  │  ├─ Autonomy Tab
│  │  ├─ Memory Tab
│  │  ├─ Radar Tab (3D)
│  │  └─ Logs Tab
│  ├─ Status Bar
│  └─ System Tray Icon
├─ Consent Modal (overlays)
├─ Notification Toast
├─ Event Listener (async)
└─ Theme Manager (dark/light)
```

---

## 📋 Six Views

### 1. Home View (Dashboard)
**Purpose:** Overview of entire system

**Components:**
- System status indicator (🟢/🟡/🟠/🔴)
- CPU/Memory/Disk gauges
- Active component count
- Recent events timeline
- Quick action buttons

**Updates:** Every 2 seconds

### 2. Sentinel View (Threats)
**Purpose:** Threat monitoring and response

**Components:**
- Threat timeline (latest first)
- Severity color coding
- Pattern name and description
- Evidence summary
- Response action buttons (Investigate, Isolate, Whitelist)
- Threat history graph

**Updates:** Real-time on detection

### 3. Autonomy View (Plans)
**Purpose:** Plan execution monitoring

**Components:**
- Active plan display
- Step-by-step execution progress
- Risk score visualization
- Estimated time remaining
- Manual override button
- Feedback form (after completion)
- Plan history

**Updates:** Step-by-step

### 4. Memory View (Knowledge)
**Purpose:** Explore episodic memory

**Components:**
- Event timeline (scrollable)
- Search by keyword/date/actor
- Semantic search (type query, see related events)
- Statistics dashboard
- Database size
- Vector index status
- Vault secrets count

**Updates:** On-demand

### 5. Radar View (3D Graph)
**Purpose:** Visualize system relationships

**Components:**
- 3D force-directed graph
- Nodes: components, processes, files, users
- Edges: relationships, data flow
- Interactive: rotate, zoom, click to inspect
- Real-time updates
- Color coding by risk level

**Updates:** Every 5 seconds

### 6. Logs View (Audit Trail)
**Purpose:** Structured logging viewer

**Components:**
- Log entry table
- Severity color coding
- Filtering (by component, severity, time)
- Full-text search
- Export to CSV/JSON
- Follow mode (tail -f)
- Statistics

**Updates:** Real-time

---

## 🔧 Key Classes

### MainWindow
```python
class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, config: Dict):
        # Initialize PyQt6
        # Setup menu bar
        # Setup tabs
        # Setup status bar
        # Connect event bus
    
    def create_menu_bar(self):
        """Create File, View, Help menus"""
    
    def create_tabs(self):
        """Create 6 tab views"""
    
    def update_metrics(self, metrics: Dict):
        """Update displayed metrics"""
    
    async def on_event(self, event: EventEnvelope):
        """Handle event from bus"""
```

### HomeTab
```python
class HomeTab(QWidget):
    """Dashboard view"""
    
    def create_gauges(self):
        """CPU, Memory, Disk gauges"""
    
    def create_timeline(self):
        """Recent events"""
    
    def update_stats(self, stats: Dict):
        """Update display"""
```

### SentinelTab
```python
class SentinelTab(QWidget):
    """Threat monitoring"""
    
    def add_threat(self, threat: Threat):
        """Add threat to timeline"""
    
    def on_threat_response(self, threat_id: str, action: str):
        """User clicked response button"""
```

### AutonomyTab
```python
class AutonomyTab(QWidget):
    """Plan execution"""
    
    def set_active_plan(self, plan: ExecutionPlan):
        """Display plan execution"""
    
    def update_step(self, plan_id: str, step_idx: int, result):
        """Update step status"""
```

### MemoryTab
```python
class MemoryTab(QWidget):
    """Knowledge exploration"""
    
    def search(self, query: str):
        """Search events"""
    
    def semantic_search(self, embedding: List[float]):
        """Search by similarity"""
```

### RadarTab
```python
class RadarTab(QWidget):
    """3D relationship graph"""
    
    def update_graph(self, nodes: List, edges: List):
        """Update visualization"""
    
    def on_node_click(self, node_id: str):
        """Show node details"""
```

### LogsTab
```python
class LogsTab(QWidget):
    """Audit trail viewer"""
    
    def add_log_entry(self, entry: LogEntry):
        """Add to table"""
    
    def filter(self, component: str, severity: str):
        """Filter logs"""
```

### ConsentModal
```python
class ConsentModal(QDialog):
    """Consent request dialog"""
    
    def __init__(self, request: ConsentRequest):
        # Display action preview
        # Show risk level
        # Risk visualization
        # PIN entry (if needed)
        # Approve/Deny/Hold buttons
    
    async def on_approve(self):
        """User approved"""
    
    async def on_deny(self):
        """User denied"""
    
    async def on_hold(self):
        """User pressed HOLD (safe word)"""
```

### SystemTrayIcon
```python
class SystemTrayIcon(QSystemTrayIcon):
    """Notification area icon"""
    
    def create_context_menu(self):
        """Show/Hide, Settings, Exit"""
    
    def show_notification(self, title: str, message: str):
        """Toast notification"""
```

### ThemeManager
```python
class ThemeManager:
    """Dark/Light theme support"""
    
    @staticmethod
    def apply_light_theme():
        """Light colors"""
    
    @staticmethod
    def apply_dark_theme():
        """Dark colors"""
    
    @staticmethod
    def get_color(name: str) -> QColor:
        """Get color by name"""
```

---

## 📁 File Structure

```
apps/gui/
├── __init__.py                  (Main GUI entry point - 100 lines)
├── main_window.py               (MainWindow - 150 lines)
├── views/
│   ├── home.py                  (Home tab - 120 lines)
│   ├── sentinel.py              (Sentinel tab - 120 lines)
│   ├── autonomy.py              (Autonomy tab - 120 lines)
│   ├── memory.py                (Memory tab - 120 lines)
│   ├── radar.py                 (Radar tab - 150 lines)
│   └── logs.py                  (Logs tab - 100 lines)
├── widgets/
│   ├── consent_modal.py         (Consent dialog - 100 lines)
│   ├── threat_card.py           (Threat display - 60 lines)
│   ├── plan_viewer.py           (Plan display - 80 lines)
│   ├── event_timeline.py        (Timeline widget - 80 lines)
│   └── gauge_widget.py          (Metric gauge - 60 lines)
├── icons/
│   ├── threat.svg
│   ├── plan.svg
│   ├── memory.svg
│   └── radar.svg
├── styles/
│   ├── light.qss                (Light theme)
│   └── dark.qss                 (Dark theme)
└── resources.qrc                (Qt resource file)

tests/
├── unit/
│   └── test_ui_components.py
└── integ/
    └── test_gui_flow.py
```

---

## 🎯 Week-by-Week Plan

### Week 1: Foundation & Layout

**Day 1-2: PyQt6 Setup**
- MainWindow creation
- Menu bar and status bar
- Tab widget setup
- 100 lines

**Day 3-4: Home & Sentinel Tabs**
- Home dashboard
- Status gauges
- Sentinel threat timeline
- 240 lines

**Day 5: Buffer**

### Week 2: Autonomy & Memory

**Day 1-2: Autonomy Tab**
- Plan display
- Step-by-step progress
- Feedback form
- 120 lines

**Day 3-4: Memory Tab**
- Event table
- Search functionality
- Semantic search
- 120 lines

**Day 5: Polish**

### Week 3: Radar & Logs

**Day 1-2: Radar Tab (3D)**
- 3D graph visualization
- Node/edge creation
- Interactive controls
- 150 lines

**Day 3-4: Logs Tab**
- Log table
- Filtering
- Export
- 100 lines

**Day 5: Integration**

### Week 4: Modals & Theming

**Day 1-2: Consent Modal**
- Rich preview
- Risk visualization
- PIN entry
- Safe word detection
- 100 lines

**Day 3-4: Theming**
- Light/dark themes
- StyleSheets
- Icon theming
- 80 lines

**Day 5: System Tray**
- Tray icon
- Context menu
- Notifications
- 60 lines

### Week 5: Testing & Polish

**Day 1-2: Unit Tests**
- Widget tests
- Modal tests

**Day 3: Integration**
- Full flow testing
- Event bus integration

**Day 4-5: Polish**
- Performance optimization
- UX refinement
- Documentation

---

## 🎨 UI Mockup

```
┌─────────────────────────────────────────────────────────────┐
│ ASTRA-OS Operator Console              🟢 [=] [-] [x]      │
├──────────┬──────────────────────────────────────────────────┤
│ File View Help │                                             │
├──────────────────────────────────────────────────────────────┤
│ │ 🏠 Home │ 🔴 Sentinel │ 🤖 Autonomy │ 🧠 Memory │...│   │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  System Status                  Resource Usage              │
│  🟢 All Systems Operational    CPU: ████░░░░░░ 45%         │
│  Components: 8/8 Online        Memory: ████████░░ 62%      │
│  Events (last hour): 1,234     Disk: ██████░░░░ 34%       │
│                                                               │
│  Recent Events                                              │
│  ├─ 14:32 - Autonomy: Plan executed (backup_download)      │
│  ├─ 14:31 - Sensor: 42 files modified in Downloads         │
│  └─ 14:30 - Memory: New episodic event stored              │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│ Connected • 🟢 Boot Daemon • 🟢 Event Bus • 🟢 All Systems   │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔌 Event Bus Integration

```python
async def setup_event_bus():
    """Connect to Event Bus for real-time updates"""
    
    bus = await EventBus()._init()
    
    # Subscribe to all topics
    await bus.subscribe("sensor.*", on_sensor_event)
    await bus.subscribe("autonomy.*", on_autonomy_event)
    await bus.subscribe("threat.*", on_threat_event)
    await bus.subscribe("consent.*", on_consent_event)
    
    async def on_sensor_event(event):
        main_window.update_from_event(event)
    
    async def on_threat_event(event):
        sentinel_tab.add_threat(event)
        if event.severity == "critical":
            show_consent_modal(event)
    
    # Continue listening
    while running:
        await asyncio.sleep(1)
```

---

## 🔒 Consent Modal Details

```python
class ConsentModal(QDialog):
    """Rich consent request dialog"""
    
    def __init__(self, request: ConsentRequest):
        super().__init__()
        
        # Risk visualization
        risk_level = get_risk_level(request.risk_score)
        risk_color = get_risk_color(risk_level)
        risk_bar = QProgressBar()
        risk_bar.setValue(int(request.risk_score * 100))
        risk_bar.setStyleSheet(f"color: {risk_color}")
        
        # Action preview
        preview = QTextEdit()
        preview.setText(request.action_preview)
        preview.setReadOnly(True)
        
        # Risk factors
        factors = QListWidget()
        for factor in request.risk_factors:
            factors.addItem(f"{factor['name']}: {factor['value']}")
        
        # PIN entry (if needed)
        if request.require_pin:
            pin_input = QLineEdit()
            pin_input.setEchoMode(QLineEdit.Password)
        
        # Buttons
        approve_btn = QPushButton("Approve")
        deny_btn = QPushButton("Deny")
        hold_btn = QPushButton("HOLD (333 STOP)")
        
        # Layout everything
        layout = QVBoxLayout()
        layout.addWidget(QLabel("CONSENT REQUEST"))
        layout.addWidget(risk_bar)
        layout.addWidget(QLabel("Action:"))
        layout.addWidget(preview)
        layout.addWidget(QLabel("Risk Factors:"))
        layout.addWidget(factors)
        if request.require_pin:
            layout.addWidget(QLabel("PIN:"))
            layout.addWidget(pin_input)
        layout.addLayout(create_button_layout(approve_btn, deny_btn, hold_btn))
        
        self.setLayout(layout)
```

---

## ⚙️ Configuration (gui.yaml)

```yaml
version: 1

gui:
  # Window
  window:
    title: "ASTRA-OS Operator Console"
    width: 1400
    height: 900
    start_minimized: false
  
  # Tabs
  tabs:
    home:
      enabled: true
      update_interval_seconds: 2
    sentinel:
      enabled: true
      update_interval_seconds: 1
    autonomy:
      enabled: true
      update_interval_seconds: 1
    memory:
      enabled: true
      update_interval_seconds: 10
    radar:
      enabled: true
      update_interval_seconds: 5
    logs:
      enabled: true
      update_interval_seconds: 1
  
  # Theme
  theme:
    default: "dark"
    allow_toggle: true
  
  # System tray
  system_tray:
    enabled: true
    minimize_to_tray: true
  
  # Hotkeys
  hotkeys:
    show_window: "Alt+S"
    safe_word: "Alt+P"
    emergency_stop: "Ctrl+Shift+Esc"
  
  # Consent modal
  consent:
    show_risk_factors: true
    show_preview: true
    require_pin_above_risk: 0.6
    timeout_seconds: 120
```

---

## 🧪 Test Cases

### Unit Tests
```python
test_main_window_creation()
test_tab_creation()
test_consent_modal()
test_theme_switching()
test_tray_icon()
```

### Integration Tests
```python
test_event_bus_integration()
test_real_time_updates()
test_user_interaction_flow()
test_consent_approval_flow()
test_safe_word_detection()
```

---

## 📊 Success Metrics

| Metric | Target |
|--------|--------|
| Startup time | < 5s |
| Tab switching | < 100ms |
| Event update latency | < 500ms |
| Memory usage | < 200MB |
| CPU usage | < 5% |
| Frame rate | 60 FPS |
| Consent modal response | < 100ms |

---

## 🚀 Integration Points

### With Event Bus
- Real-time updates from all components
- Consent modal triggering
- User actions back to bus

### With Memory Layer
- Event history display
- Semantic search
- Statistics queries

### With Sentinel
- Threat timeline
- Response actions
- Incident visualization

### With Autonomy
- Plan display
- Step execution
- Feedback submission

---

## 📦 Deliverables

### Code (1000+ lines)
- ✅ Main window
- ✅ 6 tab views (720 lines)
- ✅ Widgets (280 lines)
- ✅ Consent modal
- ✅ Theme manager
- ✅ System tray

### Assets
- ✅ Icons (SVG)
- ✅ StyleSheets (light/dark)
- ✅ Resources file

### Configuration
- ✅ gui.yaml

### Tests
- ✅ Unit tests
- ✅ Integration tests

### Documentation
- ✅ GUI_USER_GUIDE.md
- ✅ Hotkeys reference
- ✅ Troubleshooting

---

**Dependencies:**
```
PyQt6>=6.0
PyOpenGL>=3.1.5  # For 3D radar
numpy>=1.22  # Graph calculations
```

---

**Next:** Phase 15 (MSI Installer)

**Status:** 🟢 READY (after Phase 12)
