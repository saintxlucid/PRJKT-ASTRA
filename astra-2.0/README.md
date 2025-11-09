# ASTRA 2.0 - Neural OS Companion

ASTRA 2.0 is an autonomous OS companion that integrates deeply with Windows to provide intelligent automation, document processing, creative media generation, and secure system control.

## 🎯 Core Features

### OS Interface
- Windows API integration with security sandbox
- Input automation (keyboard, mouse, UI)
- Process and resource monitoring
- System event handling

### Document Intelligence
- Multi-format processing (TXT, JSON, PDF, OCR)
- Semantic embedding and search
- Vector store integration
- Document structure preservation

### Media Engine
- Stable Diffusion integration
- Text-to-video generation
- DAW automation (Ableton, FL Studio)
- Creative tool bridges

### Neural Network
- Multi-agent orchestration
- Sub-LLM delegation
- Memory consolidation
- Pattern learning

### Security
- Identity-based auth
- Permission kernel
- Activity audit
- Sandbox enforcement

## 🚀 Quick Start

1. Clone the repository
2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.\.venv\Scripts\activate   # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. Run the system:
```bash
python -m uvicorn interfaces.api.fastapi_server:app --reload
```

## 🏗️ Project Structure

```
astra-2.0/
├── core/                    # Core system components
│   ├── os_interface/       # Windows API integration
│   ├── doc_processor/      # Document handling
│   ├── media_engine/       # Creative tools bridge
│   ├── neural_network/     # AI orchestration
│   └── security/           # Security kernel
├── agents/                 # Specialized agents
│   ├── task_agents/       # System automation
│   ├── creative_agents/   # Media generation
│   └── safety_agents/     # Security monitoring
└── interfaces/            # External interfaces
    ├── gui/              # Desktop UI
    ├── api/             # HTTP/WebSocket API
    └── plugins/         # Extension system
```

## 🔒 Security Model

ASTRA 2.0 implements a comprehensive security model:

1. **Identity System**
   - Single-user focus (Saint Lucid)
   - API key authentication
   - Role-based access control

2. **Permission Kernel**
   - Fine-grained capabilities
   - Action auditing
   - Resource isolation

3. **Safety Controls**
   - Command sandboxing
   - Resource limits
   - Activity monitoring

## 📚 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Security Model](docs/SECURITY.md)
- [API Reference](docs/API.md)
- [Plugin Development](docs/PLUGINS.md)

## 🛠️ Development

1. Install dev dependencies:
```bash
pip install -r requirements-dev.txt
```

2. Run tests:
```bash
pytest
```

3. Run linting:
```bash
ruff check .
```

## 📄 License

Copyright © 2025 Saint Lucid. All rights reserved.

## 🙏 Acknowledgments

Built with guidance from Saint Lucid's vision of safe and sovereign AI companions.