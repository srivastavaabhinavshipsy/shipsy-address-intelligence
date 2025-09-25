import React, { useEffect, useState } from 'react';
import { API_URL } from '../config';

const ConnectionTest = () => {
  const [backendStatus, setBackendStatus] = useState('checking');
  const [error, setError] = useState(null);

  useEffect(() => {
    // Test direct fetch without axios
    const testConnection = async () => {
      try {
        console.log('Testing connection to backend...');
        const response = await fetch(`${API_URL}/api/health`, {
          method: 'GET',
          headers: {
            'Accept': 'application/json'
          }
        });
        
        console.log('Response status:', response.status);
        
        if (response.ok) {
          const data = await response.json();
          console.log('Backend response:', data);
          setBackendStatus('connected');
        } else {
          setBackendStatus('error');
          setError(`HTTP ${response.status}`);
        }
      } catch (err) {
        console.error('Connection error:', err);
        setBackendStatus('offline');
        setError(err.message);
      }
    };

    testConnection();
    
    // Test every 5 seconds
    const interval = setInterval(testConnection, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="fixed bottom-4 right-4 p-3 bg-white rounded-lg shadow-lg border border-gray-200 text-xs">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${
          backendStatus === 'connected' ? 'bg-green-500' : 
          backendStatus === 'checking' ? 'bg-yellow-500 animate-pulse' : 
          'bg-red-500'
        }`} />
        <span className="text-gray-700">
          Backend: {backendStatus === 'connected' ? 'Connected' :
                   backendStatus === 'checking' ? 'Checking...' :
                   'Offline'}
        </span>
      </div>
      {error && (
        <div className="text-red-600 mt-1 text-xs">
          {error}
        </div>
      )}
    </div>
  );
};

export default ConnectionTest;