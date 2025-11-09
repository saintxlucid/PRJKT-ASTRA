import * as vscode from 'vscode';
import * as path from 'path';
import { SigilGateService, Plan, Budget } from '../services/SigilGateService';

export class ConsentWebviewProvider implements vscode.WebviewViewProvider {
  private view?: vscode.WebviewView;
  private currentPlan?: Plan;
  private currentScopes?: string[];

  constructor(
    private context: vscode.ExtensionContext,
    private sigilGateService: SigilGateService
  ) {}

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    context: vscode.WebviewViewResolveContext,
    token: vscode.CancellationToken
  ): void | Thenable<void> {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [
        vscode.Uri.file(path.join(this.context.extensionPath, 'webview', 'dist'))
      ]
    };

    webviewView.webview.html = this.getEmptyStateHtml();

    // Handle messages from webview
    webviewView.webview.onDidReceiveMessage(async (message) => {
      switch (message.command) {
        case 'approve':
          await this.handleApprove(message.data);
          break;
        case 'reject':
          await this.handleReject();
          break;
        case 'requestDiff':
          await this.handleDiffRequest(message.path);
          break;
      }
    });
  }

  public async showConsentModal(plan: Plan, scopes?: string[], budget?: Budget) {
    this.currentPlan = plan;
    this.currentScopes = scopes || this.inferScopes(plan);

    if (!this.view) {
      vscode.window.showErrorMessage('Consent UI not ready');
      return;
    }

    // Get diff if file operation
    let diff = { before: '', after: '' };
    if (plan.path) {
      diff = await this.sigilGateService.getDiff(plan.path);
    }

    this.view.webview.html = this.getConsentHtml({
      plan,
      scopes: this.currentScopes,
      budget: budget || this.inferBudget(plan),
      diff
    });

    this.view.show?.(true);
  }

  private inferScopes(plan: Plan): string[] {
    const scopes: string[] = [];

    switch (plan.op) {
      case 'write':
      case 'create':
        scopes.push(`fs.write:${plan.path || '**'}`);
        break;
      case 'delete':
        scopes.push(`fs.delete:${plan.path || '**'}`);
        break;
      case 'read':
        scopes.push(`fs.read:${plan.path || '**'}`);
        break;
      case 'exec':
      case 'spawn':
        scopes.push(`proc.spawn:${plan.args?.[0] || 'cmd'}`);
        break;
      case 'network':
        scopes.push(`net.egress:*:443`);
        break;
    }

    return scopes.length > 0 ? scopes : ['unknown:*'];
  }

  private inferBudget(plan: Plan): Budget {
    // Conservative defaults
    return {
      cpu_ms: plan.timeout ? plan.timeout * 1000 : 5000,
      io_bytes: 10 * 1024 * 1024, // 10 MB
      net_bytes: 5 * 1024 * 1024, // 5 MB
      ops: 100
    };
  }

  private async handleApprove(data: any) {
    if (!this.currentPlan) {
      vscode.window.showErrorMessage('No plan to approve');
      return;
    }

    try {
      const tokenRequest = {
        kid: `k${Date.now()}`,
        sub: `proc:${process.pid}`,
        scopes: this.currentScopes || [],
        plan: this.currentPlan,
        budget: data.budget,
        expires_in_secs: 300 // 5 minutes
      };

      const result = await this.sigilGateService.createToken(tokenRequest);
      
      vscode.window.showInformationMessage(
        `✅ Operation approved. Token: ${result.token_kid}`
      );

      this.view!.webview.html = this.getEmptyStateHtml();
      this.currentPlan = undefined;
      this.currentScopes = undefined;
    } catch (error: any) {
      vscode.window.showErrorMessage(`❌ Approval failed: ${error.message}`);
    }
  }

  private async handleReject() {
    vscode.window.showInformationMessage('❌ Operation rejected by operator');
    this.view!.webview.html = this.getEmptyStateHtml();
    this.currentPlan = undefined;
    this.currentScopes = undefined;
  }

  private async handleDiffRequest(filePath: string) {
    const diff = await this.sigilGateService.getDiff(filePath);
    this.view?.webview.postMessage({ command: 'showDiff', data: diff });
  }

  private getEmptyStateHtml(): string {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          body {
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
            padding: 40px 20px;
            text-align: center;
          }
          .sigil {
            font-size: 64px;
            margin-bottom: 20px;
            opacity: 0.6;
          }
          h2 {
            font-weight: 400;
            font-size: 18px;
            color: var(--vscode-descriptionForeground);
          }
        </style>
      </head>
      <body>
        <div class="sigil">🛡️</div>
        <h2>ASTRA Sigil Gate</h2>
        <p>No pending operations</p>
        <p style="font-size: 12px; margin-top: 20px; opacity: 0.6;">
          Operator sovereignty active. All privileged operations require explicit consent.
        </p>
      </body>
      </html>
    `;
  }

  private getConsentHtml(data: {
    plan: Plan;
    scopes: string[];
    budget: Budget;
    diff: { before: string; after: string };
  }): string {
    const scopeRows = data.scopes.map((scope) => {
      const [kind, pattern] = scope.split(':');
      const isDangerous = kind.includes('write') || kind.includes('delete') || kind.includes('spawn');
      return `
        <tr>
          <td>
            <span class="scope-badge ${isDangerous ? 'danger' : 'safe'}">
              ${kind.toUpperCase()}
            </span>
          </td>
          <td><code>${pattern || '*'}</code></td>
        </tr>
      `;
    }).join('');

    const budgetPercent = (used: number, max: number) => Math.round((used / max) * 100);

    return `
      <!DOCTYPE html>
      <html>
      <head>
        <style>
          * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
          }
          body {
            font-family: var(--vscode-font-family);
            color: var(--vscode-foreground);
            background: var(--vscode-editor-background);
            padding: 20px;
          }
          .header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 2px solid var(--vscode-panel-border);
          }
          .sigil {
            font-size: 32px;
          }
          h1 {
            font-size: 20px;
            font-weight: 600;
          }
          .section {
            margin-bottom: 24px;
            background: var(--vscode-editor-background);
            border: 1px solid var(--vscode-panel-border);
            border-radius: 6px;
            padding: 16px;
          }
          .section h2 {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 12px;
            color: var(--vscode-foreground);
          }
          .plan-op {
            font-size: 18px;
            font-weight: 600;
            color: #C9B37E;
            margin-bottom: 8px;
          }
          .plan-path {
            font-family: 'Consolas', monospace;
            font-size: 13px;
            color: var(--vscode-descriptionForeground);
          }
          table {
            width: 100%;
            border-collapse: collapse;
          }
          td {
            padding: 8px 0;
            vertical-align: top;
          }
          td:first-child {
            width: 140px;
          }
          .scope-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
          }
          .scope-badge.safe {
            background: rgba(54, 199, 144, 0.15);
            color: #36C790;
          }
          .scope-badge.danger {
            background: rgba(233, 75, 53, 0.15);
            color: #E94B35;
          }
          code {
            background: var(--vscode-textCodeBlock-background);
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 12px;
          }
          .budget-bar {
            height: 8px;
            background: var(--vscode-input-background);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 6px;
          }
          .budget-fill {
            height: 100%;
            background: linear-gradient(90deg, #77DDE8, #36C790);
            transition: width 0.3s ease;
          }
          .budget-label {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            margin-bottom: 4px;
          }
          .diff {
            font-family: 'Consolas', monospace;
            font-size: 12px;
            background: var(--vscode-textCodeBlock-background);
            padding: 12px;
            border-radius: 4px;
            max-height: 200px;
            overflow-y: auto;
          }
          .diff-line {
            padding: 2px 0;
          }
          .diff-line.add {
            background: rgba(54, 199, 144, 0.1);
            color: #36C790;
          }
          .diff-line.remove {
            background: rgba(233, 75, 53, 0.1);
            color: #E94B35;
          }
          .actions {
            display: flex;
            gap: 12px;
            margin-top: 24px;
          }
          button {
            flex: 1;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 600;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s ease;
          }
          .btn-approve {
            background: linear-gradient(135deg, #77DDE8, #36C790);
            color: #0A0A0B;
          }
          .btn-approve:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(119, 221, 232, 0.3);
          }
          .btn-reject {
            background: rgba(233, 75, 53, 0.15);
            color: #E94B35;
            border: 1px solid #E94B35;
          }
          .btn-reject:hover {
            background: rgba(233, 75, 53, 0.25);
          }
          .warning {
            background: rgba(239, 182, 91, 0.1);
            border-left: 3px solid #EFB65B;
            padding: 12px;
            margin-top: 12px;
            border-radius: 4px;
            font-size: 13px;
          }
        </style>
      </head>
      <body>
        <div class="header">
          <span class="sigil">🛡️</span>
          <div>
            <h1>ASTRA Consent Required</h1>
            <p style="font-size: 12px; opacity: 0.7;">Operator approval needed for privileged operation</p>
          </div>
        </div>

        <div class="section">
          <h2>📋 Operation Plan</h2>
          <div class="plan-op">${data.plan.op.toUpperCase()}</div>
          ${data.plan.path ? `<div class="plan-path">${data.plan.path}</div>` : ''}
          ${data.plan.args ? `<div class="plan-path">Args: ${data.plan.args.join(' ')}</div>` : ''}
        </div>

        ${data.diff.before || data.diff.after ? `
          <div class="section">
            <h2>🔍 File Changes</h2>
            <div class="diff">
              ${data.diff.before.split('\n').slice(0, 10).map(line => 
                `<div class="diff-line remove">- ${line}</div>`
              ).join('')}
              ${data.diff.after.split('\n').slice(0, 10).map(line => 
                `<div class="diff-line add">+ ${line}</div>`
              ).join('')}
            </div>
          </div>
        ` : ''}

        <div class="section">
          <h2>🔐 Scopes Requested</h2>
          <table>
            ${scopeRows}
          </table>
          ${data.scopes.some(s => s.includes('write') || s.includes('delete')) ? `
            <div class="warning">
              ⚠️ <strong>Warning:</strong> This operation can modify or delete files. Review carefully.
            </div>
          ` : ''}
        </div>

        <div class="section">
          <h2>📊 Resource Budget</h2>
          <div style="margin-bottom: 12px;">
            <div class="budget-label">
              <span>CPU</span>
              <span>${data.budget.cpu_ms}ms</span>
            </div>
            <div class="budget-bar">
              <div class="budget-fill" style="width: ${budgetPercent(data.budget.cpu_ms, 10000)}%"></div>
            </div>
          </div>
          <div style="margin-bottom: 12px;">
            <div class="budget-label">
              <span>I/O</span>
              <span>${(data.budget.io_bytes / 1024 / 1024).toFixed(1)} MB</span>
            </div>
            <div class="budget-bar">
              <div class="budget-fill" style="width: ${budgetPercent(data.budget.io_bytes, 100 * 1024 * 1024)}%"></div>
            </div>
          </div>
          <div style="margin-bottom: 12px;">
            <div class="budget-label">
              <span>Network</span>
              <span>${(data.budget.net_bytes / 1024 / 1024).toFixed(1)} MB</span>
            </div>
            <div class="budget-bar">
              <div class="budget-fill" style="width: ${budgetPercent(data.budget.net_bytes, 50 * 1024 * 1024)}%"></div>
            </div>
          </div>
          <div>
            <div class="budget-label">
              <span>Operations</span>
              <span>${data.budget.ops}</span>
            </div>
            <div class="budget-bar">
              <div class="budget-fill" style="width: ${budgetPercent(data.budget.ops, 1000)}%"></div>
            </div>
          </div>
        </div>

        <div class="actions">
          <button class="btn-reject" onclick="reject()">❌ Reject</button>
          <button class="btn-approve" onclick="approve()">✅ Approve & Execute</button>
        </div>

        <script>
          const vscode = acquireVsCodeApi();

          function approve() {
            vscode.postMessage({
              command: 'approve',
              data: {
                budget: ${JSON.stringify(data.budget)}
              }
            });
          }

          function reject() {
            vscode.postMessage({
              command: 'reject'
            });
          }
        </script>
      </body>
      </html>
    `;
  }
}
