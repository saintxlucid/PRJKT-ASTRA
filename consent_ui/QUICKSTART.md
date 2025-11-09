# Consent UI VSCode Extension

## Quick Setup

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Watch mode (auto-recompile)
npm run watch

# Package extension
npm run package
# Generates: astra-consent-ui-1.0.0.vsix

# Install in VSCode
code --install-extension astra-consent-ui-1.0.0.vsix
```

## Testing

1. Press `F5` to launch Extension Development Host
2. Open ASTRA workspace
3. Run command: `Ctrl+Shift+P → "ASTRA: Show Consent Modal"`
4. Select a plan JSON file
5. Review and approve/reject

## Configuration

Set `sigilctl` path in VSCode settings:
```json
{
  "astra.sigilGate.sigilctlPath": "X:/PROJECT_ASTRA_2.0/PROJECT_ASTRA_1.0 (ASTRA_CORE)/sigil_gate/target/release/sigilctl.exe"
}
```

## Development

- `src/extension.ts` - Main extension entry point
- `src/services/SigilGateService.ts` - sigilctl integration
- `src/webview/ConsentWebviewProvider.ts` - Consent UI modal

## Requirements

- Node.js 20+
- VSCode 1.85.0+
- Sigil Gate compiled (`cargo build`)
