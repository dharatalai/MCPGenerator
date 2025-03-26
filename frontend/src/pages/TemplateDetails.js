import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { mcpService } from '../api/mcpService';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { FaFile, FaFolder, FaAngleRight, FaAngleDown, FaDownload } from 'react-icons/fa';

const TemplateDetails = () => {
  const { templateId } = useParams();
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expandedFolders, setExpandedFolders] = useState({});
  
  useEffect(() => {
    const fetchTemplateFiles = async () => {
      try {
        const response = await mcpService.getTemplateFiles(templateId);
        setFiles(response.data || []);
        
        // Select first file by default if available
        if (response.data && response.data.length > 0) {
          const firstFile = response.data.find(file => !file.is_dir);
          if (firstFile) {
            handleFileSelect(firstFile);
          }
        }
      } catch (err) {
        setError('Failed to load template files. Please try again later.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchTemplateFiles();
  }, [templateId]);
  
  const handleFileSelect = async (file) => {
    if (file.is_dir) return;
    
    setSelectedFile(file);
    setLoading(true);
    
    try {
      const response = await mcpService.getFileContent(templateId, file.path);
      setFileContent(response.data.content || '');
    } catch (err) {
      setError(`Failed to load file content: ${err.message}`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  const toggleFolder = (folderPath) => {
    setExpandedFolders(prev => ({
      ...prev,
      [folderPath]: !prev[folderPath]
    }));
  };
  
  const getFileExtension = (filename) => {
    return filename.split('.').pop().toLowerCase();
  };
  
  const getLanguage = (filename) => {
    const ext = getFileExtension(filename);
    const languageMap = {
      'py': 'python',
      'js': 'javascript',
      'jsx': 'jsx',
      'ts': 'typescript',
      'tsx': 'tsx',
      'json': 'json',
      'md': 'markdown',
      'txt': 'text',
      'env': 'bash'
    };
    
    return languageMap[ext] || 'text';
  };
  
  const buildFileTree = (files) => {
    // Group files by directory
    const filesByDir = {};
    files.forEach(file => {
      const dirPath = file.path.split('/').slice(0, -1).join('/');
      if (!filesByDir[dirPath]) {
        filesByDir[dirPath] = [];
      }
      filesByDir[dirPath].push(file);
    });
    
    // Render directory
    const renderDir = (dirPath, level = 0) => {
      const filesInDir = filesByDir[dirPath] || [];
      
      return (
        <div key={dirPath} style={{ marginLeft: `${level * 16}px` }}>
          {filesInDir.map(file => {
            if (file.is_dir) {
              const isExpanded = expandedFolders[file.path];
              return (
                <div key={file.path}>
                  <div 
                    className="flex items-center py-1 px-2 hover:bg-gray-100 cursor-pointer"
                    onClick={() => toggleFolder(file.path)}
                  >
                    {isExpanded ? <FaAngleDown className="mr-1" /> : <FaAngleRight className="mr-1" />}
                    <FaFolder className="mr-2 text-yellow-500" />
                    <span>{file.name}</span>
                  </div>
                  {isExpanded && renderDir(file.path, level + 1)}
                </div>
              );
            } else {
              return (
                <div 
                  key={file.path}
                  className={`flex items-center py-1 px-2 hover:bg-gray-100 cursor-pointer ${selectedFile && selectedFile.path === file.path ? 'bg-blue-100' : ''}`}
                  onClick={() => handleFileSelect(file)}
                >
                  <div style={{ width: '16px', marginRight: '8px' }}></div>
                  <FaFile className="mr-2 text-gray-500" />
                  <span>{file.name}</span>
                </div>
              );
            }
          })}
        </div>
      );
    };
    
    return renderDir('');
  };
  
  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Template Details</h1>
      
      {error && (
        <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-4" role="alert">
          <p>{error}</p>
        </div>
      )}
      
      {loading && !selectedFile ? (
        <div className="flex justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
        </div>
      ) : (
        <div className="flex flex-col md:flex-row gap-6">
          {/* File Explorer */}
          <div className="w-full md:w-1/3 lg:w-1/4 bg-white p-4 rounded-lg shadow-md overflow-auto max-h-[calc(100vh-200px)]">
            <h2 className="text-lg font-bold mb-3">Files</h2>
            {files.length === 0 ? (
              <p className="text-gray-500">No files available</p>
            ) : (
              buildFileTree(files)
            )}
          </div>
          
          {/* File Content */}
          <div className="w-full md:w-2/3 lg:w-3/4">
            {selectedFile ? (
              <div className="bg-white rounded-lg shadow-md overflow-hidden">
                <div className="bg-gray-100 px-4 py-2 flex justify-between items-center">
                  <h3 className="font-medium">{selectedFile.path}</h3>
                  <button 
                    className="flex items-center text-blue-500 hover:text-blue-700"
                    onClick={() => {
                      // Download file logic
                      const blob = new Blob([fileContent], { type: 'text/plain' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = selectedFile.name;
                      document.body.appendChild(a);
                      a.click();
                      document.body.removeChild(a);
                    }}
                  >
                    <FaDownload className="mr-1" /> Download
                  </button>
                </div>
                <div className="p-0 overflow-auto max-h-[calc(100vh-250px)]">
                  {loading ? (
                    <div className="flex justify-center py-12">
                      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
                    </div>
                  ) : (
                    <SyntaxHighlighter 
                      language={getLanguage(selectedFile.name)}
                      style={vscDarkPlus}
                      showLineNumbers
                      customStyle={{ margin: 0, borderRadius: 0 }}
                    >
                      {fileContent}
                    </SyntaxHighlighter>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white p-8 rounded-lg shadow-md text-center">
                <p className="text-gray-700">Select a file to view its content</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TemplateDetails; 