import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CloudArrowUpIcon, 
  DocumentTextIcon,
  XMarkIcon,
  ArrowDownTrayIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';
import { addressAPI } from '../services/api';
import toast from 'react-hot-toast';

const CSVUploader = ({ onBatchComplete }) => {
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [preview, setPreview] = useState([]);

  const onDrop = useCallback((acceptedFiles) => {
    const uploadedFile = acceptedFiles[0];
    if (uploadedFile) {
      setFile(uploadedFile);
      
      // Read first few lines for preview
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target.result;
        const lines = text.split('\n').slice(0, 6);
        setPreview(lines);
      };
      reader.readAsText(uploadedFile.slice(0, 2000)); // Read first 2KB for preview
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

  const handleUpload = async () => {
    if (!file) {
      toast.error('Please select a file first');
      return;
    }

    setIsProcessing(true);
    setProgress(0);

    try {
      // Upload file
      const response = await addressAPI.validateBatch(file);
      const { job_id } = response;
      
      toast.success('File uploaded successfully! Processing addresses...');

      // Poll for status
      const pollInterval = setInterval(async () => {
        try {
          const status = await addressAPI.getBatchStatus(job_id);
          
          setProgress(status.progress_percentage);
          
          if (status.status === 'complete') {
            clearInterval(pollInterval);
            setIsProcessing(false);
            toast.success(`Processed ${status.total} addresses successfully!`);
            onBatchComplete(status.results);
          }
        } catch (error) {
          clearInterval(pollInterval);
          setIsProcessing(false);
          toast.error('Failed to get processing status');
        }
      }, 1000); // Poll every second

    } catch (error) {
      setIsProcessing(false);
      toast.error('Failed to upload file');
      console.error('Upload error:', error);
    }
  };

  const downloadTemplate = () => {
    const csvContent = `address,contact_name,contact_phone
"123 Main Street, Sea Point, Cape Town, Western Cape, 8005",John Smith,0821234567
"PO Box 456, Johannesburg, Gauteng, 2000",Sarah Johnson,0834567890
"Unit 7B, 89 Beach Road, Umhlanga, Durban, KwaZulu-Natal, 4319",Mike Davis,0795551234`;
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'address_template.csv';
    a.click();
    window.URL.revokeObjectURL(url);
    
    toast.success('Template downloaded');
  };

  const removeFile = () => {
    setFile(null);
    setPreview([]);
    setProgress(0);
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-lg shadow-sm p-5 border border-shipsy-border"
    >
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-shipsy-darkGray">
          Batch CSV Processing
        </h2>
        
        <button
          onClick={downloadTemplate}
          className="text-sm text-shipsy-blue hover:text-shipsy-darkBlue flex items-center gap-1"
        >
          <ArrowDownTrayIcon className="h-4 w-4" />
          Download Template
        </button>
      </div>

      <AnimatePresence mode="wait">
        {!file ? (
          <motion.div
            key="dropzone"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            {...getRootProps()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-200 ${
              isDragActive 
                ? 'border-shipsy-blue bg-shipsy-lightBlue' 
                : 'border-shipsy-border hover:border-shipsy-blue hover:bg-gray-50'
            }`}
          >
            <input {...getInputProps()} />
            
            <motion.div
              animate={{ 
                y: isDragActive ? -5 : 0,
                scale: isDragActive ? 1.05 : 1
              }}
            >
              <CloudArrowUpIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              
              {isDragActive ? (
                <p className="text-shipsy-blue font-medium">Drop your CSV file here...</p>
              ) : (
                <>
                  <p className="text-gray-700 font-medium mb-2">
                    Drag & drop your CSV file here
                  </p>
                  <p className="text-sm text-gray-500">
                    or click to browse • Max 10MB • CSV format only
                  </p>
                </>
              )}
            </motion.div>
          </motion.div>
        ) : (
          <motion.div
            key="file-preview"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="space-y-4"
          >
            {/* File Info */}
            <div className="flex items-center justify-between bg-shipsy-lightGray rounded-lg p-4">
              <div className="flex items-center gap-3">
                <DocumentTextIcon className="h-10 w-10 text-shipsy-blue" />
                <div>
                  <p className="font-medium text-gray-900">{file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              </div>
              
              {!isProcessing && (
                <button
                  onClick={removeFile}
                  className="text-gray-400 hover:text-red-500 transition-colors"
                >
                  <XMarkIcon className="h-5 w-5" />
                </button>
              )}
            </div>

            {/* Preview */}
            {preview.length > 0 && (
              <div className="bg-gray-900 rounded-lg p-4 overflow-x-auto">
                <p className="text-xs text-gray-400 mb-2">Preview (first 5 rows):</p>
                <pre className="text-xs text-green-400 font-mono">
                  {preview.slice(0, 5).join('\n')}
                </pre>
              </div>
            )}

            {/* Progress Bar */}
            {isProcessing && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Processing addresses...</span>
                  <span className="text-primary-600 font-medium">{progress.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                  <motion.div
                    className="bg-gradient-to-r from-primary-500 to-primary-600 h-full rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {file && !isProcessing && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 flex justify-end"
        >
          <button
            onClick={handleUpload}
            className="px-5 py-2 bg-shipsy-blue text-white text-sm font-medium rounded hover:bg-shipsy-darkBlue transition-colors flex items-center gap-2"
          >
            <CheckCircleIcon className="h-5 w-5" />
            Process Addresses
          </button>
        </motion.div>
      )}
    </motion.div>
  );
};

export default CSVUploader;