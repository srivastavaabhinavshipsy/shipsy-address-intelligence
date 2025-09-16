import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ChevronDownIcon, 
  ChevronUpIcon,
  DocumentDuplicateIcon,
  ArrowDownTrayIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';

const ResultsTable = ({ results, onDownload }) => {
  const [expandedRows, setExpandedRows] = useState(new Set());
  const [sortField, setSortField] = useState('confidence_score');
  const [sortDirection, setSortDirection] = useState('desc');

  if (!results || results.length === 0) return null;

  const toggleRow = (id) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const copyAddress = (address) => {
    navigator.clipboard.writeText(address);
    toast.success('Address copied to clipboard');
  };

  const getStatusBadge = (level) => {
    const badges = {
      'CONFIDENT': { color: 'bg-green-100 text-green-800', icon: CheckCircleIcon },
      'LIKELY': { color: 'bg-blue-100 text-blue-800', icon: CheckCircleIcon },
      'SUSPICIOUS': { color: 'bg-amber-100 text-amber-800', icon: ExclamationTriangleIcon },
      'FAILED': { color: 'bg-red-100 text-red-800', icon: XCircleIcon }
    };
    
    const badge = badges[level] || badges['FAILED'];
    const Icon = badge.icon;
    
    return (
      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${badge.color}`}>
        <Icon className="h-3 w-3" />
        {level}
      </span>
    );
  };

  const sortedResults = [...results].sort((a, b) => {
    const aVal = a[sortField];
    const bVal = b[sortField];
    
    if (sortDirection === 'asc') {
      return aVal > bVal ? 1 : -1;
    } else {
      return aVal < bVal ? 1 : -1;
    }
  });

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Calculate summary stats
  const stats = {
    total: results.length,
    confident: results.filter(r => r.confidence_level === 'CONFIDENT').length,
    likely: results.filter(r => r.confidence_level === 'LIKELY').length,
    suspicious: results.filter(r => r.confidence_level === 'SUSPICIOUS').length,
    failed: results.filter(r => r.confidence_level === 'FAILED').length
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-2xl shadow-xl border border-gray-100"
    >
      {/* Header with Stats */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Batch Validation Results
          </h3>
          <button
            onClick={onDownload}
            className="btn-secondary text-sm flex items-center gap-2"
          >
            <ArrowDownTrayIcon className="h-4 w-4" />
            Export CSV
          </button>
        </div>
        
        {/* Summary Stats */}
        <div className="grid grid-cols-5 gap-3">
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
            <p className="text-xs text-gray-600">Total</p>
          </div>
          <div className="bg-green-50 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-green-600">{stats.confident}</p>
            <p className="text-xs text-gray-600">Confident</p>
          </div>
          <div className="bg-blue-50 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-blue-600">{stats.likely}</p>
            <p className="text-xs text-gray-600">Likely</p>
          </div>
          <div className="bg-amber-50 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-amber-600">{stats.suspicious}</p>
            <p className="text-xs text-gray-600">Suspicious</p>
          </div>
          <div className="bg-red-50 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-red-600">{stats.failed}</p>
            <p className="text-xs text-gray-600">Failed</p>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                ID
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Original Address
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th 
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:text-gray-700"
                onClick={() => handleSort('confidence_score')}
              >
                <div className="flex items-center gap-1">
                  Score
                  {sortField === 'confidence_score' && (
                    sortDirection === 'asc' ? 
                      <ChevronUpIcon className="h-3 w-3" /> : 
                      <ChevronDownIcon className="h-3 w-3" />
                  )}
                </div>
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Issues
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            <AnimatePresence>
              {sortedResults.map((result, index) => (
                <React.Fragment key={result.id}>
                  <motion.tr
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      #{result.id}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                      {result.original_address}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(result.confidence_level)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-16 bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              result.confidence_score >= 90 ? 'bg-green-500' :
                              result.confidence_score >= 70 ? 'bg-blue-500' :
                              result.confidence_score >= 50 ? 'bg-amber-500' :
                              'bg-red-500'
                            }`}
                            style={{ width: `${result.confidence_score}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-gray-700">
                          {result.confidence_score}%
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`font-medium ${
                        result.issues.length > 0 ? 'text-red-600' : 'text-green-600'
                      }`}>
                        {result.issues.length} issues
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => copyAddress(result.normalized_address)}
                          className="text-gray-400 hover:text-gray-600 transition-colors"
                          title="Copy normalized address"
                        >
                          <DocumentDuplicateIcon className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => toggleRow(result.id)}
                          className="text-gray-400 hover:text-gray-600 transition-colors"
                          title="View details"
                        >
                          {expandedRows.has(result.id) ? 
                            <ChevronUpIcon className="h-4 w-4" /> : 
                            <ChevronDownIcon className="h-4 w-4" />
                          }
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                  
                  {/* Expanded Row */}
                  <AnimatePresence>
                    {expandedRows.has(result.id) && (
                      <motion.tr
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                      >
                        <td colSpan="6" className="px-6 py-4 bg-gray-50">
                          <div className="space-y-3">
                            <div>
                              <p className="text-xs font-medium text-gray-500 uppercase">Normalized Address</p>
                              <p className="text-sm text-gray-900 mt-1">{result.normalized_address}</p>
                            </div>
                            
                            {result.issues.length > 0 && (
                              <div>
                                <p className="text-xs font-medium text-gray-500 uppercase">Issues</p>
                                <ul className="mt-1 space-y-1">
                                  {result.issues.map((issue, i) => (
                                    <li key={i} className="text-sm text-red-600 flex items-start gap-1">
                                      <span>•</span>
                                      <span>{issue}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            
                            {result.suggestions.length > 0 && (
                              <div>
                                <p className="text-xs font-medium text-gray-500 uppercase">Suggestions</p>
                                <ul className="mt-1 space-y-1">
                                  {result.suggestions.map((suggestion, i) => (
                                    <li key={i} className="text-sm text-blue-600 flex items-start gap-1">
                                      <span>💡</span>
                                      <span>{suggestion}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        </td>
                      </motion.tr>
                    )}
                  </AnimatePresence>
                </React.Fragment>
              ))}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
    </motion.div>
  );
};

export default ResultsTable;