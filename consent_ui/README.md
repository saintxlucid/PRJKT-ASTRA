# 🛡️ ASTRA Consent UI — Sigil Gate Extension

> **Sacred operator sovereignty for privileged operations**

VSCode extension providing explicit consent flow for ASTRA OS operations protected by Sigil Gate tokens.

---

## ✨ Features

### 🔐 **Consent Modal**
- Visual plan review with diff display
- Scope summary with danger indicators
- Resource budget bars (CPU, I/O, Network, Ops)
- Approve/Reject workflow

### 📊 **Token History**
- View all past approvals
- Token status tracking (active, expired, revoked)
- One-click revocation

### ⚡ **Smart Integration**
- Auto-detects `sigilctl` binary
- Maintains consent history locally
- Real-time status updates

---

## 🚀 Installation

### Prerequisites
- VSCode 1.85.0+
- Node.js 20+
- Rust toolchain (for Sigil Gate)

### Build from Source
```bash
cd consent_ui
npm install
npm run compile
```

### Package Extension
```bash
npm run package
# Generates astra-consent-ui-1.0.0.vsix
```

### Install in VSCode
```bash
code --install-extension astra-consent-ui-1.0.0.vsix
```

---

## 🎯 Usage

### Manual Consent
```
Ctrl+Shift+P → "ASTRA: Show Consent Modal"
```

Select a plan JSON file to review and approve.

### Programmatic Consent
```typescript
// From another extension or ASTRA core
await vscode.commands.executeCommand('astra.sigilGate.showConsent', {
  op: 'delete',
  path: 'X:/test.txt',
  args: [],
  timeout: 30
});
```

### View Token History
Click the 🛡️ ASTRA status bar item, or:
```
Ctrl+Shift+P → "ASTRA: View Token History"
```

### Revoke Token
```
Ctrl+Shift+P → "ASTRA: Revoke Token"
```

Enter token KID and revocation reason.

---

## ⚙️ Configuration

### `astra.sigilGate.sigilctlPath`
**Type**: `string`  
**Default**: `""` (auto-detect)

Absolute path to `sigilctl` binary. If empty, extension searches:
1. `{workspace}/sigil_gate/target/release/sigilctl.exe`
2. `{workspace}/sigil_gate/target/debug/sigilctl.exe`
3. System PATH

### `astra.sigilGate.autoApprove`
**Type**: `boolean`  
**Default**: `false`

Auto-approve low-risk operations (NOT RECOMMENDED for production).

### `astra.sigilGate.showBudgetWarnings`
**Type**: `boolean`  
**Default**: `true`

Show warnings when resource budget exceeds 80%.

---

## 📂 Extension Structure

```
consent_ui/
├── src/
│   ├── extension.ts                 ✅ Extension entry point
│   ├── services/
│   │   └── SigilGateService.ts      ✅ sigilctl integration
│   └── webview/
│       └── ConsentWebviewProvider.ts ✅ Consent modal UI
├── package.json                     ✅ Extension manifest
├── tsconfig.json                    ✅ TypeScript config
└── README.md                        ✅ This file
```

---

## 🔗 Integration with Sigil Gate

### Token Creation Flow
1. **Plan Created** → Operation details + scopes + budget
2. **Consent Modal** → Operator reviews and approves
3. **Token Issued** → `sigilctl issue` creates hybrid PQC+ECDSA token
4. **Operation Executes** → Protected by token verification
5. **Journal Entry** → Audit log with Merkle chain

### Example Plan
```json
{
  "op": "delete",
  "path": "X:/PROJECT_ASTRA_2.0/test.txt",
  "args": [],
  "timeout": 30
}
```

### Inferred Scopes
```typescript
{
  op: 'write'   → 'fs.write:path'
  op: 'delete'  → 'fs.delete:path'
  op: 'read'    → 'fs.read:path'
  op: 'exec'    → 'proc.spawn:cmd'
  op: 'network' → 'net.egress:*:443'
}
```

### Budget Defaults
```typescript
{
  cpu_ms: 5000,           // 5 seconds
  io_bytes: 10485760,     // 10 MB
  net_bytes: 5242880,     // 5 MB
  ops: 100                // 100 operations
}
```

---

## 🎨 UI Components

### Consent Modal
- **Header**: Sigil (🛡️) + "ASTRA Consent Required"
- **Plan Section**: Operation type + path + args
- **Diff Section**: Before/after file changes (if applicable)
- **Scopes Section**: Table with danger indicators
- **Budget Section**: 4 progress bars (CPU, I/O, Network, Ops)
- **Actions**: Reject (red) | Approve (lucid gradient)

### Color Palette (Obsidian Spectrum)
- **Background**: `var(--vscode-editor-background)`
- **Text**: `var(--vscode-foreground)`
- **Accent**: `#C9B37E` (limestone gold)
- **Success**: `#36C790` (lucid green)
- **Danger**: `#E94B35` (red alert)
- **Info**: `#77DDE8` (lucid teal)

---

## 🧪 Testing

### Manual Test
1. Build Sigil Gate: `cd ../sigil_gate && cargo build`
2. Create test plan:
```json
{
  "op": "write",
  "path": "X:/test.txt",
  "args": [],
  "timeout": 10
}
```
3. Open consent modal: `Ctrl+Shift+P → "ASTRA: Show Consent Modal"`
4. Select plan file
5. Review and approve
6. Verify token created in history

### Integration Test
```typescript
// Test consent flow
const plan = { op: 'delete', path: 'X:/test.txt' };
await vscode.commands.executeCommand('astra.sigilGate.showConsent', plan);
// Manually approve in UI
// Verify token in history
```

---

## 🔐 Security Properties

### Operator Sovereignty
- **Explicit consent** required for all privileged operations
- **No auto-approve** without operator review (unless configured)
- **Audit trail** maintained in local history

### Token Binding
- **Plan digest** (SHA-256) embedded in token
- **Environment attestation** (exe hash, ppid, cmdline)
- **Scope enforcement** prevents privilege escalation

### Budget Limits
- **Hard caps** on CPU, I/O, network, operations
- **Real-time tracking** during execution
- **Kill-switch** if budget exceeded

---

## 📊 Metrics

| Metric | Value |
|--------|-------|
| **Files** | 5 |
| **Lines of Code** | ~950 |
| **Dependencies** | 3 (vscode, execa, @types/node) |
| **Commands** | 3 |
| **Configuration** | 3 settings |

---

## 🗺️ Roadmap

### v1.1 (Next)
- [ ] Real-time diff viewer with syntax highlighting
- [ ] Token usage analytics dashboard
- [ ] Batch approval for low-risk operations
- [ ] Integration with ASTRA Pantheon UI

### v1.2 (Future)
- [ ] Multi-operator approval (2-of-3, 3-of-5)
- [ ] Custom policy DSL editor
- [ ] Remote consent (approve from mobile)
- [ ] Biometric unlock (Windows Hello)

### v2.0 (Vision)
- [ ] AI-powered risk scoring
- [ ] Predictive budget estimation
- [ ] Time-travel debugging (replay + rollback)
- [ ] Distributed consent (multi-machine)

---

## 📖 Related Documentation

| Document | Purpose |
|----------|---------|
| `🔐_SIGIL_GATE_V1_COMPLETE.md` | Sigil Gate core documentation |
| `🏛️_PANTHEON_SHELL_V1_COMPLETE.md` | Pantheon UI documentation |
| `_PHASE_1_2_INTEGRATION_SUMMARY.md` | Integration overview |
| `sigil_gate/README.md` | sigilctl CLI reference |

---

## 🛡️ Commands Reference

### `astra.sigilGate.showConsent`
Open consent modal for plan approval.

**Arguments**:
- `plan` (optional): Plan object or path to plan JSON file

**Example**:
```typescript
vscode.commands.executeCommand('astra.sigilGate.showConsent', {
  op: 'delete',
  path: 'X:/test.txt'
});
```

### `astra.sigilGate.viewHistory`
Open token history view with all past approvals.

**Example**:
```typescript
vscode.commands.executeCommand('astra.sigilGate.viewHistory');
```

### `astra.sigilGate.revokeToken`
Revoke a token by KID.

**Prompts**:
1. Token KID
2. Revocation reason

**Example**:
```typescript
vscode.commands.executeCommand('astra.sigilGate.revokeToken');
```

---

## 🦋 Saint Lucid Signature

**333** — Explicit. Reversible. Sovereign.

Every operation requires conscious operator approval. No hidden actions. Full transparency. Complete control.

---

## 📄 License

MIT License — Part of ASTRA OS

---

🛡️🏛️🦋💎 **Operator sovereignty, forged in limestone and light.**
