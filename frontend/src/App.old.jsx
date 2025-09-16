import React, { useState, useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';
import Layout from './components/Layout';
import SimpleAddressInput from './components/SimpleAddressInput';
import CSVUploader from './components/CSVUploader';
import ResultsPanel from './components/ResultsPanel';
import ResultsTable from './components/ResultsTable';
import MapView from './components/MapView';
import ConnectionTest from './components/ConnectionTest';
import { addressAPI } from './services/api';

function App() {
  const [activeTab, setActiveTab] = useState('single');
  const [singleResult, setSingleResult] = useState(null);
  const [batchResults, setBatchResults] = useState([]);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    loadStats();
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      await addressAPI.healthCheck();
      console.log('Backend API is healthy');
    } catch (error) {
      console.error('Backend API health check failed:', error);
    }
  };

  const loadStats = async () => {
    try {
      const data = await addressAPI.getStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const handleSingleValidation = (result) => {
    setSingleResult(result);
    loadStats(); // Refresh stats
  };

  const handleBatchComplete = (results) => {
    setBatchResults(results);
    setActiveTab('results');
    loadStats(); // Refresh stats
  };

  const handleDownloadResults = async () => {
    if (batchResults.length === 0) return;
    
    // Create CSV content
    const headers = ['ID', 'Original Address', 'Valid', 'Confidence Score', 'Confidence Level', 'Normalized Address', 'Issues', 'Suggestions'];
    const rows = batchResults.map(r => [
      r.id,
      r.original_address,
      r.is_valid,
      r.confidence_score,
      r.confidence_level,
      r.normalized_address,
      r.issues.join('; '),
      r.suggestions.join('; ')
    ]);
    
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');
    
    // Download file
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sa_logicheck_results_${new Date().getTime()}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const allResults = [...(singleResult ? [singleResult] : []), ...batchResults];

  return (
    <>
      <ConnectionTest />
      <Toaster 
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#fff',
            color: '#363636',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            borderRadius: '0.75rem',
            padding: '12px 16px',
          },
          success: {
            iconTheme: {
              primary: '#10B981',
              secondary: '#fff',
            },
          },
          error: {
            iconTheme: {
              primary: '#EF4444',
              secondary: '#fff',
            },
          },
        }}
      />
      
      <Layout stats={stats}>
        <div className="flex gap-6 h-[calc(100vh-120px)]">
          {/* Left Panel - Input Section */}
          <div className="w-1/3 min-w-[400px] space-y-4 overflow-y-auto">
            {/* Tab Navigation */}
            <div className="flex space-x-4 mb-4">
              <button
                onClick={() => setActiveTab('single')}
                className={`pb-2 px-1 border-b-2 font-medium text-sm transition-all duration-200 ${
                  activeTab === 'single'
                    ? 'border-shipsy-blue text-shipsy-blue'
                    : 'border-transparent text-shipsy-gray hover:text-shipsy-darkGray'
                }`}
              >
                Single Address
              </button>
              <button
                onClick={() => setActiveTab('batch')}
                className={`pb-2 px-1 border-b-2 font-medium text-sm transition-all duration-200 ${
                  activeTab === 'batch'
                    ? 'border-shipsy-blue text-shipsy-blue'
                    : 'border-transparent text-shipsy-gray hover:text-shipsy-darkGray'
                }`}
              >
                Batch Upload
              </button>
              {batchResults.length > 0 && (
                <button
                  onClick={() => setActiveTab('results')}
                  className={`pb-2 px-1 border-b-2 font-medium text-sm transition-all duration-200 ${
                    activeTab === 'results'
                      ? 'border-shipsy-blue text-shipsy-blue'
                      : 'border-transparent text-shipsy-gray hover:text-shipsy-darkGray'
                  }`}
                >
                  Results ({batchResults.length})
                </button>
              )}
            </div>

            {/* Tab Content */}
            <AnimatePresence mode="wait">
              {activeTab === 'single' && (
                <motion.div
                  key="single"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                >
                  <SimpleAddressInput onValidationComplete={handleSingleValidation} />
                </motion.div>
              )}
              
              {activeTab === 'batch' && (
                <motion.div
                  key="batch"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                >
                  <CSVUploader onBatchComplete={handleBatchComplete} />
                </motion.div>
              )}
              
              {activeTab === 'results' && batchResults.length > 0 && (
                <motion.div
                  key="results-info"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="bg-white rounded-2xl shadow-xl p-6 border border-gray-100"
                >
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">
                    Batch Results Overview
                  </h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                      <span className="text-sm text-gray-600">Total Processed</span>
                      <span className="font-semibold text-gray-900">{batchResults.length}</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-gray-100">
                      <span className="text-sm text-gray-600">Valid Addresses</span>
                      <span className="font-semibold text-green-600">
                        {batchResults.filter(r => r.is_valid).length}
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-2">
                      <span className="text-sm text-gray-600">Average Score</span>
                      <span className="font-semibold text-blue-600">
                        {(batchResults.reduce((sum, r) => sum + r.confidence_score, 0) / batchResults.length).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Right Panel - Map Section */}
          <div className="flex-1 flex flex-col gap-4">
            {/* Always show map */}
            <div className="flex-1">
              <MapView results={allResults} />
            </div>
            
            {/* Results Display */}
            {activeTab === 'single' && singleResult && (
              <div className="h-auto max-h-[300px] overflow-y-auto">
                <ResultsPanel result={singleResult} />
              </div>
            )}
            
            {activeTab === 'results' && batchResults.length > 0 && (
              <div className="h-auto max-h-[400px] overflow-y-auto">
                <ResultsTable 
                  results={batchResults} 
                  onDownload={handleDownloadResults}
                />
              </div>
            )}
          </div>
        </div>
      </Layout>
    </>
  );
}

export default App;