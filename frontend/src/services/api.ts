interface ApiFetchOptions extends RequestInit {
  skipRefresh?: boolean;
}

type RefreshFunction = () => Promise<string | null>;

// Single-refresh queue to prevent race conditions
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string | null) => void;
  reject: (error: any) => void;
}> = [];

const processQueue = (error: any = null, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

export async function apiFetch(
  input: RequestInfo | URL,
  init?: ApiFetchOptions,
  refreshFn?: RefreshFunction
): Promise<Response> {
  const options: RequestInit = {
    ...init,
    credentials: 'include',
  };

  let response = await fetch(input, options);

  if (response.status === 401 && refreshFn && !init?.skipRefresh) {
    // If already refreshing, queue this request
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then(token => {
        if (!token) {
          throw new Error('Authentication failed. Please log in again.');
        }
        const retryHeaders = new Headers(init?.headers);
        retryHeaders.set('Authorization', `Bearer ${token}`);
        const retryOptions: ApiFetchOptions = {
          ...options,
          headers: retryHeaders,
          skipRefresh: true,
        };
        return fetch(input, retryOptions);
      }).catch(error => {
        throw error;
      });
    }

    // Start refresh process
    isRefreshing = true;

    try {
      const newAccessToken = await refreshFn();

      if (newAccessToken) {
        // Process queued requests with new token
        processQueue(null, newAccessToken);

        const retryHeaders = new Headers(init?.headers);
        retryHeaders.set('Authorization', `Bearer ${newAccessToken}`);

        const retryOptions: ApiFetchOptions = {
          ...options,
          headers: retryHeaders,
          skipRefresh: true,
        };

        response = await fetch(input, retryOptions);
      } else {
        const error = new Error('Authentication failed. Please log in again.');
        processQueue(error, null);
        throw error;
      }
    } catch (refreshError) {
      processQueue(refreshError, null);
      console.error('Token refresh failed:', refreshError);
      throw new Error('Authentication failed. Please log in again.');
    } finally {
      isRefreshing = false;
    }
  }

  return response;
}

export async function apiRequest<T>(
  endpoint: string,
  options?: ApiFetchOptions,
  accessToken?: string | null,
  refreshFn?: RefreshFunction
): Promise<T> {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
  const url = `${baseUrl}${endpoint}`;

  const headers = new Headers(options?.headers);
  headers.set('Content-Type', 'application/json');

  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  const fetchOptions: ApiFetchOptions = {
    ...options,
    headers,
  };

  const response = await apiFetch(url, fetchOptions, refreshFn);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

export async function uploadProfilePhoto(
  file: File,
  accessToken?: string | null,
  refreshFn?: RefreshFunction
): Promise<{ photo_url: string }> {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
  const url = `${baseUrl}/api/v1/users/me/photo`;

  const formData = new FormData();
  formData.append('file', file);

  const headers = new Headers();
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }
  // Do NOT set Content-Type, let browser set it with boundary

  const fetchOptions: ApiFetchOptions = {
    method: 'POST',
    headers,
    body: formData,
  };

  const response = await apiFetch(url, fetchOptions, refreshFn);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}
