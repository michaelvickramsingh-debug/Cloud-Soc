const LIVE_AWS_API_URL = "https://4d6spw8ar6.execute-api.us-east-1.amazonaws.com/api";

export const API_BASE = import.meta.env.VITE_API_URL || LIVE_AWS_API_URL;

export async function fetchJson(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }
  return response.json();
}
