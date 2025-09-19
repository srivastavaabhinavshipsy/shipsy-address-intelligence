import React, { useState, useEffect, useRef } from 'react';
import { Toaster } from 'react-hot-toast';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  MapPinIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  PhoneIcon,
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  CloudArrowUpIcon,
  ChartBarIcon,
  BeakerIcon,
  ArrowDownTrayIcon,
  GlobeAltIcon,
  MagnifyingGlassIcon,
  InformationCircleIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';
import { addressAPI } from './services/api';
// import BulkProcessor from './components/BulkProcessor'; // Hidden for demo
import toast from 'react-hot-toast';

// Start with empty data - all validations will be real from now on
const INITIAL_DATA = [];

// Compact Address Validator Component
const AddressValidator = ({ onValidate, validationMode }) => {
  const [address, setAddress] = useState('');
  const [contactNumber, setContactNumber] = useState('');
  const [isValidating, setIsValidating] = useState(false);

  // Validate South African phone number
  const validateSouthAfricanNumber = (number) => {
    // Remove spaces and special characters
    const cleaned = number.replace(/[\s\-\(\)]/g, '');
    
    // COMMENTED OUT SA VALIDATION - Now accepts any phone number
    // Test numbers that are always accepted
    const testNumbers = ['+917985645346', '+919807872810'];
    if (testNumbers.includes(cleaned)) {
      return true;
    }
    
    // Accept any phone number with basic validation
    // Must have at least 10 digits (international or local format)
    // Can start with + for international numbers
    const basicPhoneRegex = /^(\+)?[0-9]{10,15}$/;
    return basicPhoneRegex.test(cleaned);
    
    // ORIGINAL SA VALIDATION (COMMENTED OUT):
    // South African phone number patterns:
    // +27 followed by 9 digits (international format)
    // 0 followed by 9 digits (local format)
    // Mobile numbers typically start with 06, 07, 08
    // const saPhoneRegex = /^(\+27|0)[6-8][0-9]{8}$/;
    // return saPhoneRegex.test(cleaned);
  };

  const formatPhoneNumber = (value) => {
    // Remove all non-digit characters except +
    const cleaned = value.replace(/[^\d+]/g, '');
    return cleaned;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!contactNumber.trim()) {
      toast.error('Please enter a contact number');
      return;
    }
    
    if (!validateSouthAfricanNumber(contactNumber)) {
      toast.error('Please enter a valid phone number (10-15 digits, can start with +)');
      return;
    }
    
    if (!address.trim()) {
      toast.error('Please enter an address');
      return;
    }

    setIsValidating(true);
    try {
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      const response = await fetch(`${API_URL}/api/validate-single`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({ 
          address: address.trim(),
          contact_number: contactNumber.trim(),
          validation_mode: validationMode 
        })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const result = await response.json();
      
      if (!result || typeof result.confidence_score === 'undefined') {
        throw new Error('Invalid response from server');
      }
      
      // Include contact number in the result
      onValidate({ ...result, contact_number: contactNumber.trim() });
      
      if (result.confidence_score >= 70) {
        toast.success('✅ Address validated successfully!');
      } else if (result.confidence_score >= 50) {
        toast('⚠️ Address has some issues', { 
          style: { background: '#FEF3C7', color: '#92400E' }
        });
      } else {
        toast.error('❌ Address validation failed');
      }
      
      setAddress('');
      setContactNumber('');
    } catch (error) {
      console.error('Validation error:', error);
      toast.error(error.message || 'Failed to validate address');
    } finally {
      setIsValidating(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Customer's Contact Number *
          </label>
          <div className="relative">
            <PhoneIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              value={contactNumber}
              onChange={(e) => setContactNumber(formatPhoneNumber(e.target.value))}
              placeholder="+27812345678 or 0812345678"
              className="w-full pl-10 pr-3 py-2 text-sm border border-gray-200 rounded-md focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              disabled={isValidating}
              required
            />
          </div>
        </div>
        
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">
            Customer's Address *
          </label>
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="123 Main Street, Cape Town"
              className="w-full pl-10 pr-3 py-2 text-sm border border-gray-200 rounded-md focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              disabled={isValidating}
              required
            />
          </div>
        </div>
      </div>
      
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isValidating || !address.trim() || !contactNumber.trim()}
          className="px-6 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isValidating ? 'Validating...' : 'Validate'}
        </button>
      </div>
    </form>
  );
};

// Compact Result Tile Component with Expandable Details
const CompactResultTile = ({ result, onClick, isSelected, onAction, onConfirmedAddressUpdate }) => {
  const [actionLoading, setActionLoading] = useState({ call: false, whatsapp: false });
  const [isExpanded, setIsExpanded] = useState(false);
  const [confirmedAddress, setConfirmedAddress] = useState(result.confirmed_address || null);
  const [loadingConfirmed, setLoadingConfirmed] = useState(false);
  const [agentTriggered, setAgentTriggered] = useState(result.agent_triggered || false);
  
  // Reset state when result changes (different CN)
  useEffect(() => {
    setConfirmedAddress(result.confirmed_address || null);
    setAgentTriggered(result.agent_triggered || false);
  }, [result.id]);

  // Fetch confirmed address only after agent has been triggered
  useEffect(() => {
    // Only fetch if confidence score < 90 AND agent has been triggered AND no confirmed address yet
    if (result.confidence_score < 90 && agentTriggered && !confirmedAddress) {
      fetchConfirmedAddress();
    }
  }, [result.id, agentTriggered]);
  
  const fetchConfirmedAddress = async () => {
    setLoadingConfirmed(true);
    try {
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      
      // Call real API endpoint with virtual number
      const response = await fetch(`${API_URL}/api/confirmed-address/${result.id}`, {
        headers: { 
          'ngrok-skip-browser-warning': 'true'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        
        if (data.status === 'confirmed' && data.confirmed_address) {
          const confirmedData = {
            address: data.confirmed_address.address,
            coordinates: data.confirmed_address.coordinates,
            confirmed_by: data.confirmed_address.confirmed_by || 'Customer',
            confirmed_at: data.confirmed_address.confirmed_at,
            confirmation_method: data.confirmed_address.confirmation_method,
            differences: data.confirmed_address.differences
          };
          
          setConfirmedAddress(confirmedData);
          
          // Notify parent component if selected
          if (isSelected && onConfirmedAddressUpdate) {
            onConfirmedAddressUpdate(confirmedData);
          }
        }
        // If status is 'pending', confirmed address remains null
      }
    } catch (error) {
      console.error('Failed to fetch confirmed address:', error);
    } finally {
      setLoadingConfirmed(false);
    }
  };
  
  // Poll for confirmed address updates periodically after agent trigger
  useEffect(() => {
    if (result.confidence_score < 90 && agentTriggered && !confirmedAddress) {
      const interval = setInterval(() => {
        fetchConfirmedAddress();
      }, 180000); // Poll every 180 seconds (3 minutes)
      
      return () => clearInterval(interval);
    }
  }, [result.id, confirmedAddress, agentTriggered]);
  
  // Update parent when selection changes
  useEffect(() => {
    if (isSelected && confirmedAddress && onConfirmedAddressUpdate) {
      onConfirmedAddressUpdate(confirmedAddress);
    }
  }, [isSelected, confirmedAddress]);

  const handleAction = async (actionType, e) => {
    e.stopPropagation();
    setActionLoading(prev => ({ ...prev, [actionType]: true }));
    
    // Show immediate feedback
    toast.loading(`Initiating ${actionType}...`, { id: actionType });
    
    try {
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      const contactNum = result.contact_number || '+27812345678';
      
      const response = await fetch(`${API_URL}/api/trigger-agent`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({ 
          address: result.original_address, 
          action_type: actionType,
          issues: result.issues || [],
          confidence_score: result.confidence_score,
          contact_number: contactNum,
          virtual_number: result.id,  // Pass the virtual number as reference
          components: result.components || {},  // Pass already validated components
          coordinates: result.coordinates || {}  // Pass already validated coordinates
        })
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Dismiss loading toast
      toast.dismiss(actionType);
      
      if (data.success) {
        // Mark that agent has been triggered
        setAgentTriggered(true);
        
        // Enhanced toast notifications based on action type
        if (actionType === 'call') {
          toast.success(
            `📞 Call Initiated! Dialing ${data.phone_number || contactNum}`,
            { 
              duration: 5000,
              icon: '☎️',
              style: {
                background: '#EFF6FF',
                color: '#1E40AF',
                border: '1px solid #BFDBFE'
              }
            }
          );
        } else {
          toast.success(
            `💬 WhatsApp Message Sent to ${data.phone_number || contactNum}`,
            { 
              duration: 5000,
              icon: '✅',
              style: {
                background: '#F0FDF4',
                color: '#166534',
                border: '1px solid #BBF7D0'
              }
            }
          );
        }
        
        if (onAction) onAction(result, actionType);
      } else {
        toast.error(data.error || 'Failed to trigger agent');
        console.error('Agent trigger failed:', data);
      }
    } catch (error) {
      // Dismiss loading toast
      toast.dismiss(actionType);
      toast.error(`Failed: ${error.message}`);
      console.error('Agent trigger error:', error);
    } finally {
      setActionLoading(prev => ({ ...prev, [actionType]: false }));
    }
  };

  const getStatusColor = () => {
    if (result.confidence_score >= 90) return 'bg-white border-gray-200';
    if (result.confidence_score >= 70) return 'bg-white border-gray-200';
    if (result.confidence_score >= 50) return 'bg-white border-gray-200';
    return 'bg-white border-gray-200';
  };

  const getStatusBadge = () => {
    if (result.confidence_score >= 90) return 'bg-green-50 text-green-700 border border-green-200';
    if (result.confidence_score >= 70) return 'bg-blue-50 text-blue-700 border border-blue-200';
    if (result.confidence_score >= 50) return 'bg-amber-50 text-amber-700 border border-amber-200';
    return 'bg-red-50 text-red-700 border border-red-200';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      whileHover={{ scale: 1.01 }}
      onClick={onClick}
      className={`
        p-2.5 rounded-md border cursor-pointer transition-all duration-200
        ${isSelected 
          ? 'border-blue-500 shadow-md ring-2 ring-blue-100' 
          : `${getStatusColor()} hover:shadow-md hover:border-gray-300`
        }
      `}
    >
      {/* Header Row */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-gray-400 font-mono">
            #{result.id || Math.random().toString(36).substr(2, 6).toUpperCase()}
          </span>
          {/* Confirmation Status Indicator */}
          {result.confidence_score < 90 && confirmedAddress && (
            <span className="text-xs px-1.5 py-0.5 rounded-full bg-green-100 text-green-700 font-medium flex items-center gap-1">
              <CheckCircleIcon className="h-3 w-3" />
              Confirmed
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${getStatusBadge()}`}>
            {Math.round(result.confidence_score)}%
          </span>
        </div>
      </div>

      {/* Address */}
      <p className="text-sm text-gray-800 font-medium line-clamp-2 mb-1.5" title={result.original_address}>
        {result.original_address}
      </p>

      {/* Status & Actions Row */}
      <div className="flex items-center justify-between">
        <span className={`text-xs font-medium ${
          result.confidence_score >= 90 ? 'text-green-600' :
          result.confidence_score >= 70 ? 'text-blue-600' :
          result.confidence_score >= 50 ? 'text-amber-600' :
          'text-red-600'
        }`}>
          {result.confidence_level}
        </span>
        
        {result.confidence_score < 90 && (
          <div className="flex gap-1">
            <button
              onClick={(e) => handleAction('call', e)}
              disabled={actionLoading.call}
              className="p-1 bg-blue-50 text-blue-600 rounded hover:bg-blue-100 disabled:opacity-50 transition-all duration-200 border border-blue-200"
              title="Make a Call"
            >
              <PhoneIcon className="h-3 w-3" />
            </button>
            <button
              onClick={(e) => handleAction('whatsapp', e)}
              disabled={actionLoading.whatsapp}
              className="p-1 bg-green-50 rounded hover:bg-green-100 disabled:opacity-50 transition-all duration-200 border border-green-200"
              title="Send WhatsApp"
            >
              <svg className="h-3 w-3" viewBox="0 0 24 24" fill="#25D366">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.149-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* What's Missing indicator + View Details */}
      <div className="mt-1.5 pt-1.5 border-t border-gray-100 flex items-center justify-between">
        {result.issues && result.issues.length > 0 ? (
          <div className="flex items-center gap-1">
            <ExclamationTriangleIcon className="h-3 w-3 text-amber-500" />
            <span className="text-xs text-amber-600 font-medium">
              {result.issues.length} missing
            </span>
          </div>
        ) : (
          <span className="text-xs text-green-600 font-medium">Complete</span>
        )}
        <button
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
          }}
          className="text-xs text-blue-600 hover:text-blue-700 font-medium"
        >
          {isExpanded ? 'Hide' : 'View'} Details
          <svg 
            className={`h-3 w-3 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
            fill="none" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>
      
      {/* Expandable Details Section */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="pt-2 space-y-2">
              {/* Confirmed Address Section - Only show after agent trigger */}
              {result.confidence_score < 90 && agentTriggered && (
                <div className={`rounded p-2 border ${confirmedAddress ? 'bg-green-50 border-green-200' : 'bg-gray-50 border-gray-200'}`}>
                  <div className="flex items-center justify-between mb-1">
                    <h5 className="text-xs font-semibold text-gray-700">Customer Confirmed Address:</h5>
                    {confirmedAddress && (
                      <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                        confirmedAddress.confirmation_method === 'call' 
                          ? 'bg-blue-100 text-blue-700' 
                          : 'bg-green-100 text-green-700'
                      }`}>
                        {confirmedAddress.confirmation_method === 'call' ? '📞' : '💬'} Confirmed
                      </span>
                    )}
                  </div>
                  
                  {loadingConfirmed ? (
                    <div className="flex items-center gap-2">
                      <div className="animate-spin h-3 w-3 border-2 border-gray-300 border-t-blue-600 rounded-full"></div>
                      <span className="text-xs text-gray-500">Fetching confirmed address...</span>
                    </div>
                  ) : confirmedAddress ? (
                    <div className="space-y-1">
                      <p className="text-xs text-green-700 font-medium">{confirmedAddress.address}</p>
                      <div className="flex gap-3 text-xs text-gray-600">
                        <span>📍 Lat: {confirmedAddress.coordinates?.latitude?.toFixed(6) || 'N/A'}</span>
                        <span>Lng: {confirmedAddress.coordinates?.longitude?.toFixed(6) || 'N/A'}</span>
                      </div>
                      <p className="text-xs text-gray-500">
                        Confirmed {new Date(confirmedAddress.confirmed_at).toLocaleDateString()} via {confirmedAddress.confirmation_method}
                      </p>
                    </div>
                  ) : (
                    <p className="text-xs text-gray-500 italic">Awaiting customer confirmation...</p>
                  )}
                </div>
              )}
              
              {/* What's Missing */}
              {result.issues && result.issues.length > 0 && (
                <div className="bg-amber-50 rounded p-2">
                  <h5 className="text-xs font-semibold text-amber-700 mb-1">What's Missing:</h5>
                  <ul className="space-y-0.5">
                    {result.issues.map((issue, idx) => (
                      <li key={idx} className="flex items-start gap-1">
                        <span className="text-amber-600 mt-0.5">•</span>
                        <span className="text-xs text-amber-700">{issue}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Recommendations */}
              {result.suggestions && result.suggestions.length > 0 && (
                <div className="bg-blue-50 rounded p-2">
                  <h5 className="text-xs font-semibold text-blue-700 mb-1">Recommendations:</h5>
                  <ul className="space-y-0.5">
                    {result.suggestions.map((suggestion, idx) => (
                      <li key={idx} className="flex items-start gap-1">
                        <span className="text-blue-600 mt-0.5">•</span>
                        <span className="text-xs text-blue-700">{suggestion}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {/* Normalized Address if different */}
              {result.normalized_address !== result.original_address && (
                <div className="bg-gray-50 rounded p-2">
                  <h5 className="text-xs font-semibold text-gray-700 mb-0.5">Normalized:</h5>
                  <p className="text-xs text-gray-600">{result.normalized_address}</p>
                </div>
              )}
              
              {/* Coordinates */}
              {result.coordinates && (
                <div className="flex gap-2 text-xs">
                  <span className="text-gray-500">Lat: {result.coordinates?.latitude?.toFixed(4) || 'N/A'}</span>
                  <span className="text-gray-500">Lng: {result.coordinates?.longitude?.toFixed(4) || 'N/A'}</span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// Map Component - Show both original and confirmed addresses
const MapComponent = ({ selectedResult, confirmedAddress }) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const originalMarkerRef = useRef(null);
  const confirmedMarkerRef = useRef(null);
  const lineRef = useRef(null);

  useEffect(() => {
    let isMounted = true;

    const initMap = async () => {
      if (!mapRef.current || mapInstanceRef.current) return;

      if (!document.querySelector('link[href*="leaflet.css"]')) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(link);
      }

      try {
        const L = await import('leaflet');
        
        if (isMounted && mapRef.current && !mapInstanceRef.current) {
          delete L.Icon.Default.prototype._getIconUrl;
          L.Icon.Default.mergeOptions({
            iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
            iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
            shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
          });

          mapInstanceRef.current = L.map(mapRef.current).setView([-28.4793, 24.6727], 5);
          
          L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
          }).addTo(mapInstanceRef.current);
        }
      } catch (error) {
        console.error('Error initializing map:', error);
      }
    };

    initMap();

    return () => {
      isMounted = false;
      if (mapInstanceRef.current) {
        try {
          mapInstanceRef.current.remove();
          mapInstanceRef.current = null;
        } catch (e) {
          console.error('Error removing map:', e);
        }
      }
    };
  }, []);

  useEffect(() => {
    if (!mapInstanceRef.current) return;

    const updateMarkers = async () => {
      try {
        const L = await import('leaflet');
        
        // Remove existing markers and line
        if (originalMarkerRef.current) {
          originalMarkerRef.current.remove();
          originalMarkerRef.current = null;
        }
        if (confirmedMarkerRef.current) {
          confirmedMarkerRef.current.remove();
          confirmedMarkerRef.current = null;
        }
        if (lineRef.current) {
          lineRef.current.remove();
          lineRef.current = null;
        }

        // Check if we have original address coordinates
        const hasOriginalCoords = selectedResult && selectedResult.coordinates && 
            selectedResult.coordinates.latitude != null && 
            selectedResult.coordinates.longitude != null;
        
        // Check if we have confirmed address coordinates
        const hasConfirmedCoords = confirmedAddress && confirmedAddress.coordinates && 
            confirmedAddress.coordinates.latitude != null && 
            confirmedAddress.coordinates.longitude != null;
        
        // Add marker for original address if coordinates exist
        if (hasOriginalCoords) {
          const { latitude, longitude } = selectedResult.coordinates;
          
          const iconColor = 
            selectedResult.confidence_score >= 70 ? '#10B981' :
            selectedResult.confidence_score >= 50 ? '#F59E0B' :
            '#EF4444';
          
          const originalIcon = L.divIcon({
            html: `
              <div style="
                background: ${iconColor};
                width: 16px;
                height: 16px;
                border-radius: 50%;
                border: 3px solid white;
                box-shadow: 0 2px 6px rgba(0,0,0,0.4);
                position: relative;
              ">
                <div style="
                  position: absolute;
                  top: -26px;
                  left: 50%;
                  transform: translateX(-50%);
                  background: white;
                  padding: 3px 8px;
                  border-radius: 4px;
                  font-size: 11px;
                  font-weight: bold;
                  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                  white-space: nowrap;
                ">Original</div>
              </div>
            `,
            className: 'custom-marker-original',
            iconSize: [24, 24],
            iconAnchor: [12, 12],
          });
          
          originalMarkerRef.current = L.marker([latitude, longitude], { icon: originalIcon })
            .addTo(mapInstanceRef.current)
            .bindPopup(`
              <div style="min-width: 200px;">
                <strong>Original Address</strong><br/>
                ${selectedResult.normalized_address || selectedResult.original_address}<br/>
                <span style="color: ${iconColor}; font-weight: bold;">
                  Score: ${Math.round(selectedResult.confidence_score)}%
                </span><br/>
                <small>Lat: ${latitude?.toFixed(6) || 'N/A'}, Lng: ${longitude?.toFixed(6) || 'N/A'}</small>
              </div>
            `);
        }
        
        // Add confirmed address marker if available (regardless of original coordinates)
        if (hasConfirmedCoords) {
          const confirmedIcon = L.divIcon({
            html: `
              <div style="
                background: #10B981;
                width: 24px;
                height: 24px;
                border-radius: 50%;
                border: 3px solid white;
                box-shadow: 0 2px 6px rgba(0,0,0,0.4);
                position: relative;
              ">
                <div style="
                  position: absolute;
                  top: -26px;
                  left: 50%;
                  transform: translateX(-50%);
                  background: #10B981;
                  color: white;
                  padding: 3px 8px;
                  border-radius: 4px;
                  font-size: 11px;
                  font-weight: bold;
                  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                  white-space: nowrap;
                ">Confirmed</div>
              </div>
            `,
            className: 'custom-marker-confirmed',
            iconSize: [16, 16],
            iconAnchor: [8, 8],
          });
          
          confirmedMarkerRef.current = L.marker(
            [confirmedAddress.coordinates.latitude, confirmedAddress.coordinates.longitude], 
            { icon: confirmedIcon }
          )
            .addTo(mapInstanceRef.current)
            .bindPopup(`
              <div style="min-width: 200px;">
                <strong>Confirmed Address</strong><br/>
                ${confirmedAddress.address}<br/>
                <span style="color: #10B981; font-weight: bold;">
                  ✓ Confirmed via ${confirmedAddress.confirmation_method}
                </span><br/>
                <small>Lat: ${confirmedAddress.coordinates.latitude?.toFixed(6) || 'N/A'}, Lng: ${confirmedAddress.coordinates.longitude?.toFixed(6) || 'N/A'}</small>
              </div>
            `);
          
          // Draw a line between original and confirmed locations only if both exist
          if (hasOriginalCoords) {
            const latlngs = [
              [selectedResult.coordinates.latitude, selectedResult.coordinates.longitude],
              [confirmedAddress.coordinates.latitude, confirmedAddress.coordinates.longitude]
            ];
            
            lineRef.current = L.polyline(latlngs, {
              color: '#6366F1',
              weight: 2,
              opacity: 0.6,
              dashArray: '5, 10'
            }).addTo(mapInstanceRef.current);
          }
        }
        
        // Center the map based on what coordinates are available
        if (hasOriginalCoords && hasConfirmedCoords) {
          // Both markers exist - fit bounds to show both
          const latlngs = [
            [selectedResult.coordinates.latitude, selectedResult.coordinates.longitude],
            [confirmedAddress.coordinates.latitude, confirmedAddress.coordinates.longitude]
          ];
          const bounds = L.latLngBounds(latlngs);
          mapInstanceRef.current.fitBounds(bounds, { 
            padding: [100, 100],
            maxZoom: 14
          });
          
          const currentZoom = mapInstanceRef.current.getZoom();
          if (currentZoom > 16) {
            mapInstanceRef.current.setZoom(15);
          }
        } else if (hasConfirmedCoords) {
          // Only confirmed address exists - center on it
          mapInstanceRef.current.setView(
            [confirmedAddress.coordinates.latitude, confirmedAddress.coordinates.longitude], 
            13, 
            { animate: true, duration: 0.5 }
          );
        } else if (hasOriginalCoords) {
          // Only original address exists - center on it
          mapInstanceRef.current.setView(
            [selectedResult.coordinates.latitude, selectedResult.coordinates.longitude], 
            13, 
            { animate: true, duration: 0.5 }
          );
        }
      } catch (error) {
        console.error('Error updating markers:', error);
      }
    };

    updateMarkers();
  }, [selectedResult, confirmedAddress]);

  return (
    <div className="bg-white rounded-md border border-gray-200 overflow-hidden h-full">
      <div ref={mapRef} className="w-full h-full" style={{ minHeight: '400px' }} />
    </div>
  );
};

// Main App Component
function App() {
  const [activeView, setActiveView] = useState('validate');
  const [allProcessedResults, setAllProcessedResults] = useState(INITIAL_DATA);
  const [globalStats, setGlobalStats] = useState(null);
  const [selectedResultIndex, setSelectedResultIndex] = useState(0);
  const [validateSelectedIndex, setValidateSelectedIndex] = useState(0);
  const [validationMode, setValidationMode] = useState('llm'); // Always use AI mode
  const [llmAvailable, setLlmAvailable] = useState(false);
  const [selectedConfirmedAddress, setSelectedConfirmedAddress] = useState(null);

  useEffect(() => {
    loadStats();
    checkLLMAvailability();
    loadSavedAddresses();
  }, []);
  
  const checkLLMAvailability = async () => {
    try {
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      const response = await fetch(`${API_URL}/health`, {
        headers: { 'ngrok-skip-browser-warning': 'true' }
      });
      const data = await response.json();
      setLlmAvailable(data.llm_validator === 'available');
    } catch (error) {
      console.error('Failed to check LLM availability:', error);
    }
  };

  const loadStats = async () => {
    try {
      const data = await addressAPI.getStats();
      setGlobalStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const loadSavedAddresses = async () => {
    try {
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      const response = await fetch(`${API_URL}/api/addresses/all`, {
        headers: { 'ngrok-skip-browser-warning': 'true' }
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success && data.addresses && data.addresses.length > 0) {
          // Transform the saved addresses to match our frontend format
          const savedAddresses = data.addresses.map(addr => ({
            id: addr.virtual_number,
            original_address: addr.original_address,
            normalized_address: addr.normalized_address,
            confidence_score: addr.confidence_score,
            confidence_level: addr.confidence_level,
            coordinates: addr.coordinates,
            issues: addr.issues,
            suggestions: addr.suggestions,
            components: addr.components,
            contact_number: addr.contact_number,
            validation_method: addr.validation_method,
            timestamp: addr.created_at,
            source: 'database',
            agent_triggered: addr.agent_triggered || false,
            confirmed_address: addr.confirmed_address || null  // Include if exists and agent was triggered
          }));
          
          setAllProcessedResults(savedAddresses);
          
          // Select the first result if any
          if (savedAddresses.length > 0) {
            setSelectedResultIndex(0);
          }
        }
      }
    } catch (error) {
      console.error('Failed to load saved addresses:', error);
      // If loading fails, keep INITIAL_DATA as fallback
    }
  };

  const handleSingleValidation = (result) => {
    // Use the ID from backend if available, otherwise generate one
    const newResult = { ...result, id: result.id || `VAL${Date.now()}`, source: 'single' };
    // Add new items to the beginning to maintain newest-first order
    setAllProcessedResults(prev => [newResult, ...prev]);
    // Select the newly added item which is now at index 0
    setSelectedResultIndex(0);
    setValidateSelectedIndex(0);
    loadStats();
    toast.success('Added to processed results', { duration: 2000 });
  };

  const handleBatchComplete = (results) => {
    // Add source field to bulk results
    const bulkResults = results.map(result => ({ ...result, source: 'bulk' }));
    // Add new items to the beginning to maintain newest-first order
    setAllProcessedResults(prev => [...bulkResults, ...prev]);
    loadStats();
    setActiveView('processed');
  };

  const handleResultClick = (index) => {
    setSelectedResultIndex(index);
  };

  const navigationTabs = [
    { id: 'validate', label: 'Validate', icon: BeakerIcon },
    // { id: 'bulk', label: 'Bulk Upload', icon: CloudArrowUpIcon }, // Hidden for demo
    { id: 'processed', label: 'Processed', icon: DocumentTextIcon, badge: allProcessedResults.length },
    { id: 'analytics', label: 'Analytics', icon: ChartBarIcon }
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <Toaster position="top-right" />
      
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="px-4">
          <div className="flex items-center justify-between h-12">
            <div className="flex items-center gap-3">
              <img 
                src="https://shipsy-public-assets.s3.amazonaws.com/shipsyflamingo/logo.png" 
                alt="Shipsy" 
                className="h-8 object-contain"
              />
              <div className="border-l border-gray-200 pl-3">
                <h1 className="text-sm font-semibold text-gray-900">AI Address Intelligence</h1>
                <p className="text-xs text-gray-500">Smart Address Validation</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              
              <div className="text-right">
                <p className="text-xs text-gray-500">Total Processed</p>
                <p className="text-sm font-semibold text-gray-900">{globalStats?.total_validated || allProcessedResults.length}</p>
              </div>
              <div className="text-right border-l border-gray-200 pl-4">
                <p className="text-xs text-gray-500">Success Rate</p>
                <p className="text-sm font-semibold text-green-600">{globalStats?.success_rate || 87}%</p>
              </div>
            </div>
          </div>
        </div>
        
        {/* Navigation Tabs */}
        <div className="px-4">
          <div className="flex gap-4">
            {navigationTabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveView(tab.id)}
                className={`
                  relative px-1 py-2.5 text-xs font-medium transition-all duration-200
                  ${activeView === tab.id 
                    ? 'text-blue-600 border-b-2 border-blue-600' 
                    : 'text-gray-500 hover:text-gray-700 border-b-2 border-transparent'
                  }
                `}
              >
                <div className="flex items-center gap-1.5">
                  <tab.icon className="h-3.5 w-3.5" />
                  {tab.label}
                  {tab.badge && (
                    <span className="ml-1 px-1 py-0.5 text-xs rounded bg-blue-100 text-blue-600 font-semibold">
                      {tab.badge}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-4 py-3">
        <AnimatePresence mode="wait">
          {/* Validate View */}
          {activeView === 'validate' && (
            <motion.div
              key="validate"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              {/* Search Bar */}
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-3 mb-3">
                <AddressValidator onValidate={handleSingleValidation} validationMode={validationMode} />
              </div>

              {/* Split View - Results and Map */}
              <div className="grid grid-cols-12 gap-3">
                {/* Left: Recent Results */}
                <div className="col-span-5 bg-white rounded-lg shadow-sm border border-gray-200">
                  <div className="px-3 py-2 border-b border-gray-100">
                    <div className="flex items-center justify-between">
                      <h2 className="text-xs font-semibold text-gray-700">Recent Validations</h2>
                      <span className="text-xs text-gray-400">{allProcessedResults.length} results</span>
                    </div>
                  </div>
                  <div className="p-2 max-h-[calc(100vh-280px)] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
                    <div className="grid grid-cols-1 gap-1.5">
                      {allProcessedResults.map((result, idx) => {
                        const actualIndex = idx;
                        return (
                          <CompactResultTile 
                            key={result.id || `validate-${idx}`}  // Use virtual_number as key to prevent cross-contamination
                            result={result}
                            onClick={() => {
                              setValidateSelectedIndex(actualIndex);
                              setSelectedConfirmedAddress(null); // Reset on selection change
                            }}
                            isSelected={validateSelectedIndex === actualIndex}
                            onConfirmedAddressUpdate={setSelectedConfirmedAddress}
                          />
                        );
                      })}
                    </div>
                  </div>
                </div>

                {/* Right: Map */}
                <div className="col-span-7 bg-white rounded-lg shadow-sm border border-gray-200 p-3">
                  <div className="flex items-center justify-between mb-2 px-1">
                    <h2 className="text-xs font-semibold text-gray-700">Location Map</h2>
                    {allProcessedResults[validateSelectedIndex] && (
                      <span className="text-xs text-gray-400 truncate max-w-xs">
                        {allProcessedResults[validateSelectedIndex].original_address}
                      </span>
                    )}
                  </div>
                  <div className="h-[calc(100vh-320px)] rounded overflow-hidden">
                    <MapComponent 
                      selectedResult={allProcessedResults[validateSelectedIndex]}
                      confirmedAddress={selectedConfirmedAddress}
                    />
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Bulk Upload View - Hidden for demo */}
          {/* {activeView === 'bulk' && (
            <motion.div
              key="bulk"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <BulkProcessor 
                onProcessComplete={handleBatchComplete} 
                validationMode={validationMode}
                llmAvailable={llmAvailable}
              />
            </motion.div>
          )} */}

          {/* Processed View */}
          {activeView === 'processed' && (
            <motion.div
              key="processed"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid grid-cols-12 gap-3"
            >
              {/* Left: Results List */}
              <div className="col-span-5 bg-white rounded-lg shadow-sm border border-gray-200">
                {/* Header */}
                <div className="px-3 py-2 border-b border-gray-100">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xs font-semibold text-gray-700">
                      All Processed Addresses
                    </h2>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">{allProcessedResults.length} total</span>
                      <button 
                        className="p-1 hover:bg-gray-50 rounded transition-colors"
                        onClick={() => {
                          const csv = 'address,confidence,status\n' + 
                            allProcessedResults.map(r => 
                              `"${r.original_address}",${r.confidence_score},${r.confidence_level}`
                            ).join('\n');
                          const blob = new Blob([csv], { type: 'text/csv' });
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = 'validated_addresses.csv';
                          a.click();
                        }}
                      >
                        <ArrowDownTrayIcon className="h-3.5 w-3.5 text-gray-500" />
                      </button>
                    </div>
                  </div>
                </div>
                
                {/* Results Grid */}
                <div className="p-2 max-h-[calc(100vh-180px)] overflow-y-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
                  <div className="grid grid-cols-1 gap-1.5">
                    {allProcessedResults.map((result, idx) => {
                      const actualIndex = idx;
                      return (
                        <CompactResultTile
                          key={result.id || idx}  // Use virtual_number as key to prevent cross-contamination
                          result={result}
                          onClick={() => {
                            handleResultClick(actualIndex);
                            setSelectedConfirmedAddress(null); // Reset on selection change
                          }}
                          isSelected={selectedResultIndex === actualIndex}
                          onConfirmedAddressUpdate={setSelectedConfirmedAddress}
                        />
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Right: Map */}
              <div className="col-span-7 bg-white rounded-lg shadow-sm border border-gray-200 p-3">
                <div className="flex items-center justify-between mb-2 px-1">
                  <h2 className="text-xs font-semibold text-gray-700">Location Map</h2>
                  {allProcessedResults[selectedResultIndex] && (
                    <span className="text-xs text-gray-400 truncate max-w-xs">
                      {allProcessedResults[selectedResultIndex].original_address}
                    </span>
                  )}
                </div>
                <div className="h-[calc(100vh-200px)] rounded overflow-hidden">
                  <MapComponent 
                    selectedResult={allProcessedResults[selectedResultIndex]}
                    confirmedAddress={selectedConfirmedAddress}
                  />
                </div>
              </div>
            </motion.div>
          )}

          {/* Analytics View */}
          {activeView === 'analytics' && (
            <motion.div
              key="analytics"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid grid-cols-3 gap-4"
            >
              <div className="bg-white rounded-md border border-gray-200 p-4">
                <DocumentTextIcon className="h-8 w-8 text-blue-500 mb-2" />
                <p className="text-xs text-gray-600">Total Validated</p>
                <p className="text-2xl font-bold text-gray-900">
                  {globalStats?.total_validated || allProcessedResults.length}
                </p>
              </div>

              <div className="bg-white rounded-md border border-gray-200 p-4">
                <CheckCircleIcon className="h-8 w-8 text-green-500 mb-2" />
                <p className="text-xs text-gray-600">Success Rate</p>
                <p className="text-2xl font-bold text-green-600">
                  {globalStats?.success_rate || 87}%
                </p>
              </div>

              <div className="bg-white rounded-md border border-gray-200 p-4">
                <ExclamationTriangleIcon className="h-8 w-8 text-amber-500 mb-2" />
                <p className="text-xs text-gray-600">Need Review</p>
                <p className="text-2xl font-bold text-amber-600">
                  {globalStats?.failed_validations || allProcessedResults.filter(r => r.confidence_score < 90).length}
                </p>
              </div>

              {/* Session Stats */}
              <div className="col-span-3 bg-white rounded-md border border-gray-200 p-4">
                <h3 className="text-sm font-medium text-gray-700 mb-3">Current Session Statistics</h3>
                <div className="grid grid-cols-4 gap-4">
                  <div className="text-center p-2 bg-gray-50 rounded">
                    <p className="text-lg font-bold text-blue-600">{allProcessedResults.length}</p>
                    <p className="text-xs text-gray-600">Session Total</p>
                  </div>
                  <div className="text-center p-2 bg-gray-50 rounded">
                    <p className="text-lg font-bold text-green-600">
                      {allProcessedResults.filter(r => r.confidence_score >= 90).length}
                    </p>
                    <p className="text-xs text-gray-600">High Confidence</p>
                  </div>
                  <div className="text-center p-2 bg-gray-50 rounded">
                    <p className="text-lg font-bold text-amber-600">
                      {allProcessedResults.filter(r => r.confidence_score >= 50 && r.confidence_score < 90).length}
                    </p>
                    <p className="text-xs text-gray-600">Medium</p>
                  </div>
                  <div className="text-center p-2 bg-gray-50 rounded">
                    <p className="text-lg font-bold text-red-600">
                      {allProcessedResults.filter(r => r.confidence_score < 50).length}
                    </p>
                    <p className="text-xs text-gray-600">Low</p>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}

export default App;