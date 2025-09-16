import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import {
  CloudArrowUpIcon,
  DocumentTextIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  PhoneIcon,
  ChatBubbleLeftRightIcon,
  ArrowDownTrayIcon,
  ArrowRightIcon
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

const BulkProcessor = ({ onProcessComplete, validationMode = 'rule', llmAvailable = false }) => {
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedAddresses, setProcessedAddresses] = useState([]);
  const [showResults, setShowResults] = useState(false);
  const [actionLoading, setActionLoading] = useState({});
  const [stats, setStats] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(null);

  const onDrop = useCallback((acceptedFiles) => {
    const uploadedFile = acceptedFiles[0];
    if (uploadedFile) {
      setFile(uploadedFile);
      setShowResults(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.csv']
    },
    maxFiles: 1,
    maxSize: 10485760, // 10MB
  });

  const handleProcess = async () => {
    if (!file) {
      toast.error('Please select a file first');
      return;
    }

    setIsProcessing(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('validation_mode', validationMode);

    try {
      // Upload and process
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      const response = await fetch(`${API_URL}/api/validate-batch`, {
        method: 'POST',
        headers: {
          'ngrok-skip-browser-warning': 'true'
        },
        body: formData
      });

      const data = await response.json();
      const jobId = data.job_id;

      // Poll for results
      const pollInterval = setInterval(async () => {
        const statusResponse = await fetch(`${API_URL}/api/batch-status/${jobId}`, {
          headers: { 'ngrok-skip-browser-warning': 'true' }
        });
        const status = await statusResponse.json();

        if (status.status === 'complete') {
          clearInterval(pollInterval);
          
          // Add coordinates to results (mock geocoding)
          const resultsWithCoords = status.results.map(result => ({
            ...result,
            coordinates: getCoordinatesForCity(result.components?.city || '')
          }));
          
          setProcessedAddresses(resultsWithCoords);
          setShowResults(true);
          setIsProcessing(false);
          
          // Calculate stats
          const validCount = resultsWithCoords.filter(r => r.confidence_score >= 90).length;
          const reviewCount = resultsWithCoords.filter(r => r.confidence_score >= 50 && r.confidence_score < 90).length;
          const invalidCount = resultsWithCoords.filter(r => r.confidence_score < 50).length;
          const avgScore = resultsWithCoords.reduce((sum, r) => sum + r.confidence_score, 0) / resultsWithCoords.length;
          
          setStats({
            total: status.total,
            valid: validCount,
            needsReview: reviewCount,
            invalid: invalidCount,
            averageScore: avgScore
          });
          
          toast.success(
            <div>
              <strong>✅ Batch Processing Complete!</strong>
              <p className="text-sm mt-1">{validCount} valid, {reviewCount} need review, {invalidCount} invalid</p>
            </div>,
            { duration: 6000 }
          );
          onProcessComplete(resultsWithCoords);
        }
      }, 1000);

    } catch (error) {
      setIsProcessing(false);
      toast.error('Failed to process file');
      console.error('Processing error:', error);
    }
  };

  // Helper function to get coordinates
  const getCoordinatesForCity = (city) => {
    const cityCoords = {
      'Cape Town': { latitude: -33.9249, longitude: 18.4241 },
      'Johannesburg': { latitude: -26.2041, longitude: 28.0473 },
      'Durban': { latitude: -29.8587, longitude: 31.0218 },
      'Pretoria': { latitude: -25.7479, longitude: 28.2293 },
      'Port Elizabeth': { latitude: -33.9608, longitude: 25.6022 },
      'Bloemfontein': { latitude: -29.0852, longitude: 26.1596 },
      'Polokwane': { latitude: -23.9045, longitude: 29.4686 },
      'Kimberley': { latitude: -28.7323, longitude: 24.7622 },
      'Stellenbosch': { latitude: -33.9321, longitude: 18.8602 },
      'Pinetown': { latitude: -29.8149, longitude: 30.8717 }
    };
    
    for (const [cityName, coords] of Object.entries(cityCoords)) {
      if (city && (cityName.toLowerCase().includes(city.toLowerCase()) || city.toLowerCase().includes(cityName.toLowerCase()))) {
        return coords;
      }
    }
    
    // Default coordinates for unknown cities
    return { latitude: -28.4793 + (Math.random() - 0.5) * 5, longitude: 24.6727 + (Math.random() - 0.5) * 5 };
  };

  const triggerAgent = async (address, actionType, addressId) => {
    setActionLoading(prev => ({ ...prev, [`${addressId}_${actionType}`]: true }));
    
    try {
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      const response = await fetch(`${API_URL}/api/trigger-agent`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({ address, action_type: actionType })
      });

      const data = await response.json();
      
      if (data.success) {
        toast.success(
          <div>
            <strong>{actionType === 'call' ? '📞 Call Agent Triggered!' : '💬 WhatsApp Agent Triggered!'}</strong>
            <p className="text-sm mt-1">Reference: {data.reference_number}</p>
          </div>,
          { duration: 5000 }
        );
        
        // Update the address status
        setProcessedAddresses(prev => prev.map(addr => 
          addr.id === addressId 
            ? { ...addr, [`${actionType}_triggered`]: true }
            : addr
        ));
      } else {
        toast.error('Failed to trigger agent');
      }
    } catch (error) {
      toast.error('Failed to trigger agent');
      console.error('Agent trigger error:', error);
    } finally {
      setActionLoading(prev => ({ ...prev, [`${addressId}_${actionType}`]: false }));
    }
  };

  const downloadResults = () => {
    if (processedAddresses.length === 0) return;

    const csvContent = [
      ['Original Address', 'Normalized Address', 'Confidence Score', 'Status', 'Issues', 'Suggestions'].join(','),
      ...processedAddresses.map(addr => [
        `"${addr.original_address}"`,
        `"${addr.normalized_address}"`,
        addr.confidence_score,
        addr.confidence_level,
        `"${addr.issues.join('; ')}"`,
        `"${addr.suggestions.join('; ')}"`
      ].join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `processed_addresses_${Date.now()}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    toast.success('Results downloaded');
  };

  return (
    <div className="space-y-6">
      {/* Upload Section */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Bulk Address Processing</h3>
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-1 rounded-full font-medium ${
              validationMode === 'llm' 
                ? 'bg-blue-100 text-blue-700' 
                : 'bg-gray-100 text-gray-700'
            }`}>
              {validationMode === 'llm' ? '🤖 AI Mode' : '📋 Rule Mode'}
            </span>
          </div>
        </div>
        {validationMode === 'llm' && !llmAvailable && (
          <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-xs text-amber-700">
              ⚠️ LLM validation requested but not configured. Please set GEMINI_API_KEY in backend .env file.
            </p>
          </div>
        )}
        
        {!file ? (
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all ${
              isDragActive 
                ? 'border-blue-500 bg-blue-50' 
                : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
            }`}
          >
            <input {...getInputProps()} />
            <CloudArrowUpIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            {isDragActive ? (
              <p className="text-blue-600 font-medium">Drop your CSV file here...</p>
            ) : (
              <>
                <p className="text-gray-700 font-medium mb-2">
                  Drag & drop your CSV file here
                </p>
                <p className="text-sm text-gray-500">
                  or click to browse • Max 10MB • CSV format
                </p>
                {validationMode === 'llm' && llmAvailable && (
                  <p className="text-xs text-blue-600 mt-2">
                    🤖 AI validation enabled for enhanced accuracy
                  </p>
                )}
              </>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between bg-gray-50 rounded-lg p-4">
              <div className="flex items-center gap-3">
                <DocumentTextIcon className="h-10 w-10 text-blue-600" />
                <div>
                  <p className="font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>
              
              {!isProcessing && (
                <button
                  onClick={() => {
                    setFile(null);
                    setShowResults(false);
                    setProcessedAddresses([]);
                  }}
                  className="text-gray-400 hover:text-red-500"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              )}
            </div>

            {!showResults && (
              <button
                onClick={handleProcess}
                disabled={isProcessing || (validationMode === 'llm' && !llmAvailable)}
                className="w-full px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
              >
                {isProcessing 
                  ? 'Processing...' 
                  : validationMode === 'llm' 
                    ? '🤖 Process with AI'
                    : 'Process Addresses'
                }
              </button>
            )}
          </div>
        )}
      </div>

      {/* Processing Stats - Show after processing */}
      {showResults && stats && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow-sm border border-blue-200 p-6 mb-6"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Processing Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
              <p className="text-xs text-gray-600">Total Processed</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">{stats.valid}</p>
              <p className="text-xs text-gray-600">Valid Addresses</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-amber-600">{stats.needsReview}</p>
              <p className="text-xs text-gray-600">Need Review</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-red-600">{stats.invalid}</p>
              <p className="text-xs text-gray-600">Invalid</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-600">{Math.round(stats.averageScore)}%</p>
              <p className="text-xs text-gray-600">Avg. Confidence</p>
            </div>
          </div>
          
          <div className="mt-4 pt-4 border-t border-blue-200">
            <p className="text-sm text-gray-700">
              <strong>💰 Estimated ROI:</strong> {Math.round((stats.valid / stats.total) * 100)}% delivery success rate • 
              {stats.needsReview} addresses flagged for agent verification • 
              Potential savings: ${(stats.needsReview * 15).toFixed(0)} in failed delivery costs
            </p>
          </div>
        </motion.div>
      )}

      {/* Results Table - When upload is complete but not showing detailed results */}
      {showResults && processedAddresses.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xl font-bold text-gray-900">
                Processing Complete
              </h3>
              <p className="text-sm text-gray-600 mt-1">{processedAddresses.length} addresses processed successfully</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={downloadResults}
                className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium"
              >
                <ArrowDownTrayIcon className="h-4 w-4" />
                Download CSV
              </button>
              <button
                onClick={() => onProcessComplete(processedAddresses)}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                View in Processed Tab
                <ArrowRightIcon className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Address
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Score
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Issues
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {processedAddresses.slice(0, 10).map((addr, index) => (
                  <tr key={addr.id || index} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-900">
                      {addr.original_address}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        addr.confidence_score >= 90
                          ? 'bg-green-100 text-green-800'
                          : addr.confidence_score >= 70
                          ? 'bg-blue-100 text-blue-800'
                          : addr.confidence_score >= 50
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {Math.round(addr.confidence_score)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`font-medium ${
                        addr.confidence_score >= 70 ? 'text-green-600' : 'text-amber-600'
                      }`}>
                        {addr.confidence_level}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {addr.issues?.length || 0} issues
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {processedAddresses.length > 10 && (
              <div className="text-center py-3 text-sm text-gray-600">
                Showing 10 of {processedAddresses.length} results. Click "View in Processed Tab" to see all.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default BulkProcessor;