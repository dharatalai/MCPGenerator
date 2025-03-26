import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance with base URL
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for authentication
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Authentication services
const authService = {
  login: async (email, password) => {
    const response = await apiClient.post('/auth/signin', { email, password });
    if (response.data.session) {
      localStorage.setItem('token', response.data.session);
    }
    return response.data;
  },
  
  register: async (email, password) => {
    const response = await apiClient.post('/auth/signup', { email, password });
    if (response.data.session) {
      localStorage.setItem('token', response.data.session);
    }
    return response.data;
  },
  
  logout: () => {
    localStorage.removeItem('token');
  }
};

// MCP Generator services
const mcpService = {
  // Generate MCP server
  generateMCPServer: async (docUrl, requestMessage, apiCredentials) => {
    return apiClient.post('/generators/generate', {
      doc_url: docUrl,
      request_message: requestMessage,
      api_credentials: apiCredentials
    });
  },
  
  // Check generation status
  checkHealth: async () => {
    return apiClient.get('/health');
  },
  
  // Get list of templates
  getTemplates: async () => {
    return apiClient.get('/generators/list-templates');
  },
  
  // Get generated files for a template
  getTemplateFiles: async (templateId) => {
    return apiClient.get(`/generators/template-files/${templateId}`);
  },
  
  // Get file content
  getFileContent: async (templateId, filePath) => {
    return apiClient.get(`/generators/file-content/${templateId}`, {
      params: { file_path: filePath }
    });
  }
};

export { authService, mcpService }; 