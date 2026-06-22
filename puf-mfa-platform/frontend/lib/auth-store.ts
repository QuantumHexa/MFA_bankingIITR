const ACCESS_KEY = "sv_access_token";
const REFRESH_KEY = "sv_refresh_token";

function readStorage(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (value) sessionStorage.setItem(key, value);
    else sessionStorage.removeItem(key);
  } catch {
    /* private browsing */
  }
}

let accessToken: string | null = readStorage(ACCESS_KEY);
let refreshToken: string | null = readStorage(REFRESH_KEY);

export const authStore = {
  getToken: () => accessToken,
  getRefresh: () => refreshToken,
  setTokens: (access: string, refresh: string) => {
    accessToken = access || null;
    refreshToken = refresh || null;
    writeStorage(ACCESS_KEY, accessToken);
    writeStorage(REFRESH_KEY, refreshToken);
  },
  clear: () => {
    accessToken = null;
    refreshToken = null;
    writeStorage(ACCESS_KEY, null);
    writeStorage(REFRESH_KEY, null);
  },
};
