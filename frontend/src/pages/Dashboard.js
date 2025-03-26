import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { mcpService } from '../api/mcpService';

const Dashboard = () => {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        const response = await mcpService.getTemplates();
        setTemplates(response.data || []);
      } catch (err) {
        setError('Failed to load templates. Please try again later.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchTemplates();
  }, []);
  
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Your MCP Templates</h1>
        <Link 
          to="/generate" 
          className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        >
          Generate New
        </Link>
      </div>
      
      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4" role="alert">
          <p>{error}</p>
        </div>
      )}
      
      {loading ? (
        <div className="flex justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      ) : templates.length === 0 ? (
        <div className="bg-gray-100 p-8 rounded-lg text-center">
          <p className="text-gray-700 mb-4">You don't have any MCP templates yet</p>
          <Link 
            to="/generate" 
            className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
          >
            Generate Your First Template
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
          {templates.map((template) => (
            <div key={template.id} className="bg-white rounded-lg shadow-md overflow-hidden">
              <div className="p-6">
                <h2 className="text-xl font-bold mb-2 truncate">{template.name || 'Untitled Template'}</h2>
                <p className="text-gray-700 mb-4 h-12 overflow-hidden">
                  {template.description || 'No description available'}
                </p>
                <div className="flex justify-between items-center text-sm text-gray-500">
                  <span>Created: {new Date(template.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <div className="px-6 py-3 bg-gray-50">
                <Link 
                  to={`/templates/${template.id}`}
                  className="text-blue-500 hover:text-blue-700 font-medium"
                >
                  View Details →
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard; 