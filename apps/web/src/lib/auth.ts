const TOKEN_KEY = "xautopilot_token";
const EMAIL_KEY = "xautopilot_email";

export function saveToken(token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

export function saveUserEmail(email: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem(EMAIL_KEY, email);
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getUserEmail(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(EMAIL_KEY);
}

export function clearToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
  }
}

/** Ping the API on production so Render free tier wakes before slow actions. */
export function warmApiHealth(): void {
  if (typeof window === "undefined") return;
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") return;
  void fetch("https://xautopilot-api.onrender.com/health").catch(() => {});
}
