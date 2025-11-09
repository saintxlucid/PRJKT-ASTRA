// ASTRA OS Configuration
// Update these values to point to your ASTRA API server

export const API_URL = "http://localhost:8080";
export const WS_URL = "ws://localhost:8080/ws";
export const API_VERSION = "v1";

export const ENDPOINTS = {
  chat: `${API_URL}/v1/chat/completions`,
  health: `${API_URL}/v1/system/health`,
  conversations: `${API_URL}/v1/conversations`,
  memory: `${API_URL}/v1/memory`,
  bridge: `${API_URL}/v1/bridge`,
};

export const DEFAULT_MODEL = "GPT-OSS-20B";
export const DEFAULT_TEMPERATURE = 0.7;
export const DEFAULT_MAX_TOKENS = 2048;
