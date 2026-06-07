let accessToken: string | null = null;
let refreshToken: string | null = null;

export const authStore = {
  getToken: () => accessToken,
  getRefresh: () => refreshToken,
  setTokens: (access: string, refresh: string) => {
    accessToken = access || null;
    refreshToken = refresh || null;
  },
  clear: () => {
    accessToken = null;
    refreshToken = null;
  },
};
