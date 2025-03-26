import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { mcpService } from '../api/mcpService';

const Generator = () => {
  const [docUrl, setDocUrl] = useState('');
  const [requestMessage, setRequestMessage] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      // First check if server is healthy
      await mcpService.checkHealth();
      
      // Submit generation request
      const response = await mcpService.generateMCPServer(
        docUrl,
        requestMessage,
        { api_key: apiKey }
      );
      
      if (response.data.success) {
        navigate(`/templates/${response.data.template_id}`);
      } else {
        setError(response.data.error || 'Failed to generate MCP server.');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Server error. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto bg-white p-8 rounded-lg shadow-md">
      <h1 className="text-2xl font-bold mb-6">Generate MCP Server</h1>
      
      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4" role="alert">
          <p>{error}</p>
        </div>
      )}
      
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="docUrl">
            API Documentation URL
          </label>
          <input
            id="docUrl"
            type="url"
            value={docUrl}
            onChange={(e) => setDocUrl(e.target.value)}
            placeholder="https://petstore.swagger.io/v2/swagger.json"
            className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
            required
          />
          <p className="text-gray-600 text-xs mt-1">
            URL to OpenAPI/Swagger documentation (JSON or YAML)
          </p>
        </div>
        
        <div className="mb-4">
          <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="requestMessage">
            Request Message
          </label>
          <textarea
            id="requestMessage"
            value={requestMessage}
            onChange={(e) => setRequestMessage(e.target.value)}
            placeholder="Generate an MCP server for this API with rate limiting and error handling"
            className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline h-32"
            required
          />
          <p className="text-gray-600 text-xs mt-1">
            Describe what you want the generated MCP server to do
          </p>
        </div>
        
        <div className="mb-6">
          <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="apiKey">
            API Key (Optional)
          </label>
          <input
            id="apiKey"
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          />
          <p className="text-gray-600 text-xs mt-1">
            If the API requires authentication, provide your API key
          </p>
        </div>
        
        <div className="flex items-center justify-between">
          <button
            type="submit"
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
            disabled={loading}
          >
            {loading ? 'Generating...' : 'Generate MCP Server'}
          </button>
        </div>
        
        {loading && (
          <div className="mt-6">
            <p className="text-gray-700">
              This may take a few minutes. Please be patient...
            </p>
            <div className="mt-2 relative w-full h-4 bg-gray-200 rounded">
              <div className="absolute top-0 left-0 h-full bg-blue-500 rounded animate-pulse w-full"></div>
            </div>
          </div>
        )}
      </form>
    </div>
  );
};

export default Generator; 