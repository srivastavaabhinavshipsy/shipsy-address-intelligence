import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircleIcon, 
  ExclamationTriangleIcon, 
  XCircleIcon,
  DocumentDuplicateIcon,
  MapPinIcon,
  InformationCircleIcon,
  LightBulbIcon
} from '@heroicons/react/24/outline';
import ConfidenceGauge from './ConfidenceGauge';
import toast from 'react-hot-toast';

const ResultsPanel = ({ result }) => {
  if (!result) return null;

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        className="space-y-6"
      >
        {/* Main Result Card */}
        <div className="bg-white rounded-lg border border-shipsy-border p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-shipsy-darkGray">
              Validation Result
            </h3>
            <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold ${
              result.confidence_level === 'CONFIDENT' ? 'bg-green-100 text-green-800' :
              result.confidence_level === 'LIKELY' ? 'bg-blue-100 text-blue-800' :
              result.confidence_level === 'SUSPICIOUS' ? 'bg-amber-100 text-amber-800' :
              'bg-red-100 text-red-800'
            }`}>
              {result.confidence_level}
            </span>
          </div>
          
          <div className="flex items-center justify-center">
            <ConfidenceGauge 
              score={result.confidence_score} 
              level={result.confidence_level}
            />
          </div>
        </div>

        {/* Address Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Original Address */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-white rounded-lg shadow-sm p-4 border border-shipsy-border"
          >
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold text-gray-900 flex items-center gap-2">
                <MapPinIcon className="h-5 w-5 text-gray-500" />
                Original Address
              </h4>
            </div>
            <p className="text-gray-700 leading-relaxed">
              {result.original_address}
            </p>
          </motion.div>

          {/* Normalized Address */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white rounded-lg shadow-sm p-4 border border-shipsy-border"
          >
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold text-gray-900 flex items-center gap-2">
                <CheckCircleIcon className="h-5 w-5 text-green-500" />
                Normalized Address
              </h4>
              <button
                onClick={() => copyToClipboard(result.normalized_address)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <DocumentDuplicateIcon className="h-5 w-5" />
              </button>
            </div>
            <p className="text-gray-700 leading-relaxed">
              {result.normalized_address}
            </p>
          </motion.div>
        </div>

        {/* Components Breakdown */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-xl shadow-lg p-5 border border-gray-100"
        >
          <h4 className="font-semibold text-gray-900 mb-4">Address Components</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {Object.entries(result.components).map(([key, value]) => (
              <div key={key} className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500 capitalize mb-1">
                  {key.replace(/_/g, ' ')}
                </p>
                <p className="font-medium text-gray-900">
                  {value || '-'}
                </p>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Issues and Suggestions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Issues */}
          {result.issues && result.issues.length > 0 && (
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
              className="bg-red-50 rounded-xl p-5 border border-red-200"
            >
              <h4 className="font-semibold text-red-900 mb-3 flex items-center gap-2">
                <InformationCircleIcon className="h-5 w-5" />
                Issues Found
              </h4>
              <ul className="space-y-2">
                {result.issues.map((issue, index) => (
                  <motion.li
                    key={index}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.5 + index * 0.1 }}
                    className="flex items-start gap-2"
                  >
                    <span className="text-red-500 mt-0.5">•</span>
                    <span className="text-sm text-red-800">{issue}</span>
                  </motion.li>
                ))}
              </ul>
            </motion.div>
          )}

          {/* Suggestions */}
          {result.suggestions && result.suggestions.length > 0 && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
              className="bg-blue-50 rounded-xl p-5 border border-blue-200"
            >
              <h4 className="font-semibold text-blue-900 mb-3 flex items-center gap-2">
                <LightBulbIcon className="h-5 w-5" />
                Suggestions
              </h4>
              <ul className="space-y-2">
                {result.suggestions.map((suggestion, index) => (
                  <motion.li
                    key={index}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.5 + index * 0.1 }}
                    className="flex items-start gap-2"
                  >
                    <span className="text-blue-500 mt-0.5">💡</span>
                    <span className="text-sm text-blue-800">{suggestion}</span>
                  </motion.li>
                ))}
              </ul>
            </motion.div>
          )}
        </div>

        {/* Metadata */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="flex items-center justify-between text-xs text-gray-500 bg-gray-50 rounded-lg p-3"
        >
          <span>Processing Time: {result.processing_time_ms}ms</span>
          <span>Validated at: {new Date(result.timestamp).toLocaleString()}</span>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default ResultsPanel;