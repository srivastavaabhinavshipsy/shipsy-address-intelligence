import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  XCircleIcon
} from '@heroicons/react/24/outline';
import { addressAPI } from '../services/api';
import toast from 'react-hot-toast';

const AddressInput = ({ onValidationComplete }) => {
  const [address, setAddress] = useState('');
  const [isValidating, setIsValidating] = useState(false);
  const [provinces, setProvinces] = useState([]);
  const [formData, setFormData] = useState({
    street: '',
    suburb: '',
    city: '',
    province: '',
    postalCode: ''
  });
  const [useStructured] = useState(false);

  useEffect(() => {
    loadProvinces();
  }, []);

  const loadProvinces = async () => {
    try {
      const response = await addressAPI.getProvinces();
      setProvinces(response.provinces);
    } catch (error) {
      console.error('Failed to load provinces:', error);
    }
  };

  const handleValidate = async () => {
    const addressToValidate = useStructured 
      ? `${formData.street}, ${formData.suburb}, ${formData.city}, ${formData.province}, ${formData.postalCode}`.replace(/,\s*,/g, ',').replace(/,\s*$/, '')
      : address;

    if (!addressToValidate.trim()) {
      toast.error('Please enter an address');
      return;
    }

    console.log('Starting validation for address:', addressToValidate);
    setIsValidating(true);
    
    try {
      const result = await addressAPI.validateSingle(addressToValidate);
      
      console.log('Validation successful, result:', result);
      
      // Show toast based on confidence level
      if (result.confidence_level === 'CONFIDENT') {
        toast.success('Address validated successfully!');
      } else if (result.confidence_level === 'LIKELY') {
        toast.success('Address validated with minor issues');
      } else if (result.confidence_level === 'SUSPICIOUS') {
        toast('Address has several issues', {
          icon: '⚠️',
          style: {
            background: '#FEF3C7',
            color: '#92400E',
          },
        });
      } else {
        toast.error('Address validation failed');
      }
      
      onValidationComplete(result);
    } catch (error) {
      console.error('Full error object:', error);
      console.error('Error response:', error.response);
      console.error('Error message:', error.message);
      
      // Check if it's a network error
      if (!error.response) {
        console.error('Network error - backend might not be running');
        toast.error('Cannot connect to server. Please ensure the backend is running.');
      } else {
        const errorMessage = error.response?.data?.error || 'Validation failed. Please try again.';
        toast.error(errorMessage);
      }
    } finally {
      setIsValidating(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleValidate();
    }
  };


  const clearForm = () => {
    setAddress('');
    setFormData({
      street: '',
      suburb: '',
      city: '',
      province: '',
      postalCode: ''
    });
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-lg shadow-sm p-5 border border-shipsy-border"
    >
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-shipsy-darkGray">
          Check Address
        </h2>
        
      </div>

      <AnimatePresence mode="wait">
        {!useStructured ? (
          <motion.div
            key="freetext"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
          >
            <div className="space-y-4">
              <div className="relative">
                <textarea
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Enter full address (e.g., 123 Main Street, Sea Point, Cape Town, Western Cape, 8005)"
                  className="w-full px-3 py-2 border border-shipsy-border rounded focus:ring-1 focus:ring-shipsy-blue focus:border-shipsy-blue transition-all duration-200 bg-white min-h-[80px] resize-none text-sm"
                  disabled={isValidating}
                />
                {address && (
                  <motion.button
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    onClick={clearForm}
                    className="absolute top-3 right-3 text-gray-400 hover:text-gray-600"
                  >
                    <XCircleIcon className="h-5 w-5" />
                  </motion.button>
                )}
              </div>

            </div>
          </motion.div>
        ) : (
          <motion.div
            key="structured"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-4"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Street Address</label>
                <input
                  type="text"
                  value={formData.street}
                  onChange={(e) => setFormData({...formData, street: e.target.value})}
                  placeholder="123 Main Street"
                  className="input-field"
                  disabled={isValidating}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Suburb</label>
                <input
                  type="text"
                  value={formData.suburb}
                  onChange={(e) => setFormData({...formData, suburb: e.target.value})}
                  placeholder="Sea Point"
                  className="input-field"
                  disabled={isValidating}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
                <input
                  type="text"
                  value={formData.city}
                  onChange={(e) => setFormData({...formData, city: e.target.value})}
                  placeholder="Cape Town"
                  className="input-field"
                  disabled={isValidating}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Province</label>
                <select
                  value={formData.province}
                  onChange={(e) => setFormData({...formData, province: e.target.value})}
                  className="input-field"
                  disabled={isValidating}
                >
                  <option value="">Select Province</option>
                  {provinces.map(prov => (
                    <option key={prov.code} value={prov.name}>
                      {prov.name} ({prov.code})
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Postal Code</label>
                <input
                  type="text"
                  value={formData.postalCode}
                  onChange={(e) => setFormData({...formData, postalCode: e.target.value})}
                  placeholder="8005"
                  maxLength="4"
                  className="input-field"
                  disabled={isValidating}
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="flex items-center justify-end mt-5 space-x-3">
        <button
          onClick={clearForm}
          className="px-4 py-2 text-sm text-shipsy-gray hover:text-shipsy-darkGray transition-colors"
          disabled={isValidating || (!address && !formData.street)}
        >
          Cancel
        </button>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleValidate}
          disabled={isValidating}
          className="px-5 py-2 bg-shipsy-blue text-white text-sm font-medium rounded hover:bg-shipsy-darkBlue transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isValidating ? (
            <>
              <span className="inline-block animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-2"></span>
              Validating...
            </>
          ) : (
            'Validate'
          )}
        </motion.button>
      </div>
    </motion.div>
  );
};

export default AddressInput;