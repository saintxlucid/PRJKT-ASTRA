import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs/promises';
import { execa } from 'execa';

export interface Plan {
  op: string;
  path?: string;
  args?: string[];
  paths?: string[];
  env?: Record<string, string>;
  timeout?: number;
}

export interface Budget {
  cpu_ms: number;
  io_bytes: number;
  net_bytes: number;
  ops: number;
}

export interface TokenRequest {
  kid: string;
  sub: string;
  scopes: string[];
  plan: Plan;
  budget?: Budget;
  expires_in_secs: number;
}

export interface TokenResponse {
  token_kid: string;
  token_path: string;
  seal_id?: number;
}

export class SigilGateService {
  private sigilctlPath: string = '';
  private dbPath: string = '';
  private historyPath: string = '';

  constructor(private context: vscode.ExtensionContext) {
    this.initialize();
  }

  private async initialize() {
    const config = vscode.workspace.getConfiguration('astra.sigilGate');
    this.sigilctlPath = config.get('sigilctlPath', '');

    // Auto-detect sigilctl if not configured
    if (!this.sigilctlPath) {
      const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
      if (workspaceRoot) {
        const possiblePaths = [
          path.join(workspaceRoot, 'sigil_gate', 'target', 'release', 'sigilctl.exe'),
          path.join(workspaceRoot, 'sigil_gate', 'target', 'debug', 'sigilctl.exe'),
          'sigilctl' // System PATH
        ];

        for (const testPath of possiblePaths) {
          try {
            await execa(testPath, ['--version']);
            this.sigilctlPath = testPath;
            console.log(`✅ Found sigilctl at: ${testPath}`);
            break;
          } catch {
            // Continue searching
          }
        }
      }
    }

    // Set database path
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (workspaceRoot) {
      this.dbPath = path.join(workspaceRoot, 'sigil_gate', 'sigil_gate.db');
      this.historyPath = path.join(this.context.globalStorageUri.fsPath, 'consent_history.json');
    }

    // Ensure history file exists
    try {
      await fs.mkdir(path.dirname(this.historyPath), { recursive: true });
      try {
        await fs.access(this.historyPath);
      } catch {
        await fs.writeFile(this.historyPath, JSON.stringify([]));
      }
    } catch (error) {
      console.error('Failed to initialize history:', error);
    }
  }

  async createToken(request: TokenRequest): Promise<TokenResponse> {
    if (!this.sigilctlPath) {
      throw new Error('sigilctl not found. Please configure astra.sigilGate.sigilctlPath');
    }

    const planPath = path.join(this.context.globalStorageUri.fsPath, `plan-${Date.now()}.json`);
    await fs.writeFile(planPath, JSON.stringify(request.plan, null, 2));

    const args = [
      'issue',
      '--kid', request.kid,
      '--sub', request.sub,
      '--scopes', request.scopes.join(','),
      '--plan', planPath,
      '--expires-in-secs', request.expires_in_secs.toString()
    ];

    if (request.budget) {
      args.push('--budget', JSON.stringify(request.budget));
    }

    try {
      const { stdout } = await execa(this.sigilctlPath, args);
      const result = JSON.parse(stdout);
      
      // Save to history
      await this.addToHistory({
        token_kid: result.token_kid || request.kid,
        scopes: request.scopes,
        plan: request.plan,
        created_at: new Date().toISOString(),
        approved: true,
        status: 'active'
      });

      return {
        token_kid: result.token_kid || request.kid,
        token_path: result.token_path || '',
        seal_id: result.seal_id
      };
    } catch (error: any) {
      throw new Error(`Token creation failed: ${error.message}`);
    }
  }

  async verifyToken(tokenPath: string): Promise<boolean> {
    if (!this.sigilctlPath) {
      throw new Error('sigilctl not found');
    }

    try {
      await execa(this.sigilctlPath, ['verify', '--token', tokenPath]);
      return true;
    } catch {
      return false;
    }
  }

  async revokeToken(tokenKid: string, reason: string): Promise<void> {
    if (!this.sigilctlPath) {
      throw new Error('sigilctl not found');
    }

    const args = [
      'revoke',
      '--token-kid', tokenKid,
      '--reason', reason,
      '--db', this.dbPath,
      '--operator', process.env.USERNAME || 'system'
    ];

    await execa(this.sigilctlPath, args);

    // Update history
    const history = await this.getTokenHistory();
    const updated = history.map(entry =>
      entry.token_kid === tokenKid
        ? { ...entry, status: 'revoked', revoked_at: new Date().toISOString(), revoke_reason: reason }
        : entry
    );
    await fs.writeFile(this.historyPath, JSON.stringify(updated, null, 2));
  }

  async getTokenHistory(): Promise<any[]> {
    try {
      const content = await fs.readFile(this.historyPath, 'utf-8');
      return JSON.parse(content);
    } catch {
      return [];
    }
  }

  private async addToHistory(entry: any): Promise<void> {
    const history = await this.getTokenHistory();
    history.push(entry);
    await fs.writeFile(this.historyPath, JSON.stringify(history, null, 2));
  }

  async getDiff(planPath: string): Promise<{ before: string; after: string }> {
    // For file operations, compute diff
    try {
      const planContent = await fs.readFile(planPath, 'utf-8');
      const plan = JSON.parse(planContent);

      if (plan.path && plan.op !== 'delete') {
        try {
          const beforeContent = await fs.readFile(plan.path, 'utf-8');
          return {
            before: beforeContent,
            after: plan.content || '(file will be created)'
          };
        } catch {
          return {
            before: '(file does not exist)',
            after: plan.content || '(new file)'
          };
        }
      }
    } catch (error) {
      console.error('Diff computation failed:', error);
    }

    return { before: '', after: '' };
  }
}
