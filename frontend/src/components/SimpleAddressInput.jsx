import React, { useState } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';

const SimpleAddressInput = ({ onValidationComplete }) => {
  const [address, setAddress] = useState('');
  const [isValidating, setIsValidating] = useState(false);

  const handleValidate = async () => {
    if (!address.trim()) {
      toast.error('Please enter an address');
      return;
    }

    setIsValidating(true);
    console.log('Validating:', address);

    try {
      // Direct fetch call to avoid any axios issues
      const API_URL = 'http://localhost:5000';
      const response = await fetch(`${API_URL}/api/validate-single`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ address: address.trim() })
      });

      console.log('Response status:', response.status);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('Result:', result);

      // Show appropriate toast
      if (result.confidence_score >= 70) {
        toast.success(`Address validated! Score: ${result.confidence_score}%`);
      } else if (result.confidence_score >= 50) {
        toast(`Address has issues. Score: ${result.confidence_score}%`, {
          icon: '⚠️',
          style: {
            background: '#FEF3C7',
            color: '#92400E',
          },
        });
      } else {
        toast.error(`Address validation failed. Score: ${result.confidence_score}%`);
      }

      onValidationComplete(result);
    } catch (error) {
      console.error('Validation error:', error);
      toast.error(`Error: ${error.message}`);
    } finally {
      setIsValidating(false);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-lg shadow-sm p-5 border border-gray-200"
    >
      <h2 className="text-lg font-semibold text-gray-800 mb-4">
        Check Address
      </h2>

      <div className="space-y-4">
        <textarea
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Enter address (e.g., 123 Main Street, Cape Town, Western Cape, 8001)"
          className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent min-h-[80px] text-sm"
          disabled={isValidating}
        />

        <div className="flex justify-end space-x-3">
          <button
            onClick={() => setAddress('')}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
            disabled={!address || isValidating}
          >
            Clear
          </button>

          <button
            onClick={handleValidate}
            disabled={isValidating || !address.trim()}
            className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isValidating ? 'Validating...' : 'Validate'}
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export default SimpleAddressInput;