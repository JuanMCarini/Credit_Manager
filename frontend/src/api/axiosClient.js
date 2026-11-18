import axios from 'axios';

const API_URL = ""; // Vite proxy will handle /api

const axiosClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach the auth token and handle FormData properly
axiosClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
      if (typeof config.headers.delete === 'function') {
        config.headers.delete('Content-Type');
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

let isRedirecting401 = false;

// Normalize FastAPI/Pydantic error details into a plain display string
const formatErrorDetail = (detail) => {
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (d && typeof d === 'object' ? (d?.msg || JSON.stringify(d)) : String(d)))
      .join('; ');
  }
  if (detail && typeof detail === 'object') {
    return JSON.stringify(detail);
  }
  return detail;
};

// Response interceptor for centralized error handling
axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error.response || error.message);
    
    // Redirect to login if token is expired or unauthorized
    if (error.response && error.response.status === 401) {
      if (!isRedirecting401) {
        isRedirecting401 = true;
        alert("Su sesión ha expirado por inactividad. Por favor, vuelva a iniciar sesión.");
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.removeItem('userRole');
        window.location.href = '/login';
      }
    }

    if (
      error.response?.data &&
      typeof error.response.data === 'object' &&
      !(error.response.data instanceof Blob) &&
      error.response.data.detail !== undefined
    ) {
      error.response.data.detail = formatErrorDetail(error.response.data.detail);
    }

    const rawDetail = error.response?.data instanceof Blob ? null : error.response?.data?.detail;
    const message = rawDetail || error.message || "An unknown error occurred";
    const customError = new Error(message);
    customError.response = error.response;
    return Promise.reject(customError);
  }
);

// Utility for handling file downloads like Excel
export const downloadFile = async (url, params = {}, defaultFilename = 'download.xlsx') => {
  try {
    const response = await axiosClient.get(url, {
      params,
      responseType: 'blob', // crucial for file downloads
    });
    
    // Extract filename from header if available
    let filename = defaultFilename;
    const disposition = response.headers['content-disposition'];
    if (disposition && disposition.indexOf('attachment') !== -1) {
      const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
      const matches = filenameRegex.exec(disposition);
      if (matches != null && matches[1]) { 
        filename = matches[1].replace(/['"]/g, '');
      }
    }

    // Create blob link to download
    const urlBlob = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = urlBlob;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.parentNode.removeChild(link);
    window.URL.revokeObjectURL(urlBlob);
  } catch (error) {
    console.error("Error downloading file:", error);
    if (error.response?.data instanceof Blob) {
      let extractedMessage = null;
      try {
        const text = await error.response.data.text();
        if (text) {
          extractedMessage = text;
          try {
            const parsed = JSON.parse(text);
            if (parsed && parsed.detail !== undefined) {
              extractedMessage = formatErrorDetail(parsed.detail);
              error.response.data = { ...parsed, detail: extractedMessage };
            }
          } catch {
            // Keep plain text when response body is not JSON
          }
        }
      } catch {
        // Ignore Blob read failures and fall through to original error
      }
      if (extractedMessage) {
        const blobError = new Error(extractedMessage);
        blobError.response = error.response;
        throw blobError;
      }
    }
    throw error;
  }
};

export default axiosClient;
