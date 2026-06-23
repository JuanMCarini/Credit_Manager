import axios from 'axios';

const API_URL = ""; // Vite proxy will handle /api

const axiosClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach the auth token
axiosClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for centralized error handling
axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error.response || error.message);
    const message = error.response?.data?.detail || error.message || "An unknown error occurred";
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
    throw error;
  }
};

export default axiosClient;
