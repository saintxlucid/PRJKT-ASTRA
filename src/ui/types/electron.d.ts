/**
 * Type definitions for Electron IPC interface
 */

export {};

declare global {
  interface Window {
    electron: {
      on(channel: string, callback: (data: any) => void): void;
      removeAllListeners(channel: string): void;
      invoke(channel: string, ...args: any[]): Promise<any>;
      send(channel: string, ...args: any[]): void;
    }
  }
}