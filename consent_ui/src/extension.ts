import * as vscode from 'vscode';
import * as path from 'path';
import { execa } from 'execa';
import { ConsentWebviewProvider } from './webview/ConsentWebviewProvider';
import { SigilGateService } from './services/SigilGateService';

let consentProvider: ConsentWebviewProvider | undefined;
let sigilGateService: SigilGateService | undefined;

export function activate(context: vscode.ExtensionContext) {
  console.log('🏛️ ASTRA Consent UI — Sigil Gate activated');

  // Initialize services
  sigilGateService = new SigilGateService(context);
  consentProvider = new ConsentWebviewProvider(context, sigilGateService);

  // Register webview provider
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      'astra.sigilGate.consentView',
      consentProvider
    )
  );

  // Command: Show consent modal
  context.subscriptions.push(
    vscode.commands.registerCommand('astra.sigilGate.showConsent', async (plan?: any) => {
      if (!consentProvider) {
        vscode.window.showErrorMessage('Consent UI not initialized');
        return;
      }

      // If no plan provided, prompt for plan file
      if (!plan) {
        const planFile = await vscode.window.showOpenDialog({
          canSelectFiles: true,
          canSelectFolders: false,
          canSelectMany: false,
          filters: { 'Plan Files': ['json'] },
          title: 'Select Plan File'
        });

        if (!planFile || planFile.length === 0) {
          return;
        }

        const planContent = await vscode.workspace.fs.readFile(planFile[0]);
        plan = JSON.parse(Buffer.from(planContent).toString('utf8'));
      }

      await consentProvider.showConsentModal(plan);
    })
  );

  // Command: View token history
  context.subscriptions.push(
    vscode.commands.registerCommand('astra.sigilGate.viewHistory', async () => {
      const panel = vscode.window.createWebviewPanel(
        'astra.sigilGate.history',
        'ASTRA Token History',
        vscode.ViewColumn.One,
        {
          enableScripts: true,
          retainContextWhenHidden: true
        }
      );

      const history = await sigilGateService?.getTokenHistory();
      panel.webview.html = getHistoryHtml(history || []);
    })
  );

  // Command: Revoke token
  context.subscriptions.push(
    vscode.commands.registerCommand('astra.sigilGate.revokeToken', async () => {
      const tokenKid = await vscode.window.showInputBox({
        prompt: 'Enter token kid to revoke',
        placeHolder: 'k1234567890'
      });

      if (!tokenKid) {
        return;
      }

      const reason = await vscode.window.showInputBox({
        prompt: 'Reason for revocation',
        placeHolder: 'Security incident / User request / etc.'
      });

      if (!reason) {
        return;
      }

      try {
        await sigilGateService?.revokeToken(tokenKid, reason);
        vscode.window.showInformationMessage(`✅ Token ${tokenKid} revoked`);
      } catch (error) {
        vscode.window.showErrorMessage(`❌ Failed to revoke: ${error}`);
      }
    })
  );

  // Status bar item
  const statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100
  );
  statusBarItem.text = '$(shield) ASTRA';
  statusBarItem.tooltip = 'ASTRA Sigil Gate — Operator Sovereignty Active';
  statusBarItem.command = 'astra.sigilGate.viewHistory';
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  console.log('✅ ASTRA Consent UI ready');
}

export function deactivate() {
  console.log('🏛️ ASTRA Consent UI deactivated');
}

function getHistoryHtml(history: any[]): string {
  const rows = history.map((entry, i) => `
    <tr>
      <td>${i + 1}</td>
      <td><code>${entry.token_kid}</code></td>
      <td>${entry.scopes.join(', ')}</td>
      <td>${entry.status}</td>
      <td>${new Date(entry.created_at).toLocaleString()}</td>
      <td>${entry.approved ? '✅' : '❌'}</td>
    </tr>
  `).join('');

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {
          font-family: var(--vscode-font-family);
          color: var(--vscode-foreground);
          background: var(--vscode-editor-background);
          padding: 20px;
        }
        table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 20px;
        }
        th, td {
          padding: 12px;
          text-align: left;
          border-bottom: 1px solid var(--vscode-panel-border);
        }
        th {
          font-weight: 600;
          color: var(--vscode-foreground);
          background: var(--vscode-editor-background);
        }
        code {
          background: var(--vscode-textCodeBlock-background);
          padding: 2px 6px;
          border-radius: 3px;
          font-size: 0.9em;
        }
        h1 {
          margin-top: 0;
          color: var(--vscode-foreground);
        }
      </style>
    </head>
    <body>
      <h1>🔐 ASTRA Token History</h1>
      <p>Total operations: ${history.length}</p>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Token KID</th>
            <th>Scopes</th>
            <th>Status</th>
            <th>Created</th>
            <th>Approved</th>
          </tr>
        </thead>
        <tbody>
          ${rows}
        </tbody>
      </table>
    </body>
    </html>
  `;
}
