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
import BulkProcessor from './components/BulkProcessor';
import toast from 'react-hot-toast';

// Sample demo data
const DEMO_DATA = [
  {
    id: 'DEMO001',
    original_address: '123 Main Street, Cape Town, Western Cape, 8001',
    normalized_address: '123 Main Street, Cape Town, Western Cape, 8001',
    confidence_score: 95,
    confidence_level: 'CONFIDENT',
    coordinates: { latitude: -33.9249, longitude: 18.4241 },
    issues: [],
    suggestions: [],
    components: {
      street_address: '123 Main Street',
      city: 'Cape Town',
      province: 'Western Cape',
      postal_code: '8001'
    }
  },
  {
    id: 'DEMO002',
    original_address: '456 Beach Road, Durban',
    normalized_address: '456 Beach Road, Durban, KwaZulu-Natal',
    confidence_score: 72,
    confidence_level: 'LIKELY',
    coordinates: { latitude: -29.8587, longitude: 31.0218 },
    issues: ['Missing postal code'],
    suggestions: ['Add postal code for better accuracy'],
    components: {
      street_address: '456 Beach Road',
      city: 'Durban',
      province: 'KwaZulu-Natal'
    }
  },
  {
    id: 'DEMO003',
    original_address: 'Johannesburg, Gauteng',
    normalized_address: 'Johannesburg, Gauteng',
    confidence_score: 45,
    confidence_level: 'SUSPICIOUS',
    coordinates: { latitude: -26.2041, longitude: 28.0473 },
    issues: ['Missing street address', 'Missing postal code'],
    suggestions: ['Provide street address', 'Add postal code'],
    components: {
      city: 'Johannesburg',
      province: 'Gauteng'
    }
  }
];

// Compact Address Validator Component
const AddressValidator = ({ onValidate, validationMode }) => {
  const [address, setAddress] = useState('');
  const [isValidating, setIsValidating] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
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
      
      onValidate(result);
      
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
    } catch (error) {
      console.error('Validation error:', error);
      toast.error(error.message || 'Failed to validate address');
    } finally {
      setIsValidating(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <div className="flex-1 relative">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Enter address (e.g., 123 Main Street, Cape Town)"
          className="w-full pl-10 pr-3 py-2 text-sm border border-gray-200 rounded-md focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
          disabled={isValidating}
        />
      </div>
      <button
        type="submit"
        disabled={isValidating || !address.trim()}
        className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isValidating ? 'Validating...' : 'Validate'}
      </button>
    </form>
  );
};

// Compact Result Tile Component with Expandable Details
const CompactResultTile = ({ result, onClick, isSelected, onAction }) => {
  const [actionLoading, setActionLoading] = useState({ call: false, whatsapp: false });
  const [isExpanded, setIsExpanded] = useState(false);

  const handleAction = async (actionType, e) => {
    e.stopPropagation();
    setActionLoading(prev => ({ ...prev, [actionType]: true }));
    
    try {
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';
      const response = await fetch(`${API_URL}/api/trigger-agent`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({ address: result.original_address, action_type: actionType })
      });

      const data = await response.json();
      
      if (data.success) {
        toast.success(
          <div>
            <strong>{actionType === 'call' ? '📞 Call Agent Triggered!' : '💬 WhatsApp Agent Triggered!'}</strong>
            <p className="text-xs mt-1">Reference: {data.reference_number}</p>
          </div>,
          { duration: 5000 }
        );
        if (onAction) onAction(result, actionType);
      } else {
        toast.error('Failed to trigger agent');
      }
    } catch (error) {
      toast.error('Failed to trigger agent');
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
        <span className="text-xs text-gray-400 font-mono">
          #{result.id || Math.random().toString(36).substr(2, 6).toUpperCase()}
        </span>
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
              className="p-1 bg-green-50 text-green-600 rounded hover:bg-green-100 disabled:opacity-50 transition-all duration-200 border border-green-200"
              title="Send WhatsApp"
            >
              <ChatBubbleLeftRightIcon className="h-3 w-3" />
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
                  <span className="text-gray-500">Lat: {result.coordinates.latitude.toFixed(4)}</span>
                  <span className="text-gray-500">Lng: {result.coordinates.longitude.toFixed(4)}</span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// Map Component - Show only selected address
const MapComponent = ({ selectedResult }) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);

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

    const updateMarker = async () => {
      try {
        const L = await import('leaflet');
        
        // Remove existing marker
        if (markerRef.current) {
          markerRef.current.remove();
          markerRef.current = null;
        }

        // Add marker for selected result only
        if (selectedResult && selectedResult.coordinates) {
          const { latitude, longitude } = selectedResult.coordinates;
          
          const iconColor = 
            selectedResult.confidence_score >= 70 ? '#10B981' :
            selectedResult.confidence_score >= 50 ? '#F59E0B' :
            '#EF4444';
          
          const customIcon = L.divIcon({
            html: `
              <div style="
                background: ${iconColor};
                width: 16px;
                height: 16px;
                border-radius: 50%;
                border: 3px solid white;
                box-shadow: 0 2px 6px rgba(0,0,0,0.4);
              "></div>
            `,
            className: 'custom-marker',
            iconSize: [16, 16],
            iconAnchor: [8, 8],
          });
          
          markerRef.current = L.marker([latitude, longitude], { icon: customIcon })
            .addTo(mapInstanceRef.current)
            .bindPopup(`
              <div style="min-width: 200px;">
                <strong>${selectedResult.normalized_address || selectedResult.original_address}</strong><br/>
                <span style="color: ${iconColor}; font-weight: bold;">
                  Score: ${Math.round(selectedResult.confidence_score)}%
                </span><br/>
                <small>Lat: ${latitude.toFixed(4)}, Lng: ${longitude.toFixed(4)}</small>
              </div>
            `)
            .openPopup();
          
          // Center map on the marker
          mapInstanceRef.current.setView([latitude, longitude], 13, {
            animate: true,
            duration: 0.5
          });
        }
      } catch (error) {
        console.error('Error updating marker:', error);
      }
    };

    updateMarker();
  }, [selectedResult]);

  return (
    <div className="bg-white rounded-md border border-gray-200 overflow-hidden h-full">
      <div ref={mapRef} className="w-full h-full" style={{ minHeight: '400px' }} />
    </div>
  );
};

// Main App Component
function App() {
  const [activeView, setActiveView] = useState('validate');
  const [allProcessedResults, setAllProcessedResults] = useState(DEMO_DATA);
  const [globalStats, setGlobalStats] = useState(null);
  const [selectedResultIndex, setSelectedResultIndex] = useState(0);
  const [validateSelectedIndex, setValidateSelectedIndex] = useState(0);
  const [validationMode, setValidationMode] = useState('rule'); // 'rule' or 'llm'
  const [llmAvailable, setLlmAvailable] = useState(false);

  useEffect(() => {
    loadStats();
    checkLLMAvailability();
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

  const handleSingleValidation = (result) => {
    const newResult = { ...result, id: `VAL${Date.now()}` };
    setAllProcessedResults(prev => [...prev, newResult]);
    setSelectedResultIndex(allProcessedResults.length);
    loadStats();
    toast.success('Added to processed results', { duration: 2000 });
  };

  const handleBatchComplete = (results) => {
    setAllProcessedResults(prev => [...prev, ...results]);
    loadStats();
    setActiveView('processed');
  };

  const handleResultClick = (index) => {
    setSelectedResultIndex(index);
  };

  const navigationTabs = [
    { id: 'validate', label: 'Validate', icon: BeakerIcon },
    { id: 'bulk', label: 'Bulk Upload', icon: CloudArrowUpIcon },
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
              <div className="p-1.5 bg-blue-50 rounded">
                <MapPinIcon className="h-5 w-5 text-blue-600" />
              </div>
              <div className="border-l border-gray-200 pl-3">
                <h1 className="text-sm font-semibold text-gray-900">AI Address Intelligence</h1>
                <p className="text-xs text-gray-500">Powered by Shipsy</p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {/* Validation Mode Toggle */}
              <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-0.5">
                <button
                  onClick={() => setValidationMode('rule')}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                    validationMode === 'rule' 
                      ? 'bg-white text-blue-600 shadow-sm' 
                      : 'text-gray-600 hover:text-gray-800'
                  }`}
                >
                  Rule-Based
                </button>
                <button
                  onClick={() => setValidationMode('llm')}
                  disabled={!llmAvailable}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                    validationMode === 'llm' 
                      ? 'bg-white text-blue-600 shadow-sm' 
                      : llmAvailable 
                        ? 'text-gray-600 hover:text-gray-800'
                        : 'text-gray-400 cursor-not-allowed'
                  }`}
                  title={!llmAvailable ? 'LLM not configured. Set GEMINI_API_KEY in backend .env file' : 'Use AI-powered validation'}
                >
                  <span className="flex items-center gap-1">
                    AI (Gemini)
                    {validationMode === 'llm' && (
                      <span className="inline-block w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse"></span>
                    )}
                  </span>
                </button>
              </div>
              
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
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-xs font-semibold text-gray-700">Quick Address Validation</h2>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      validationMode === 'llm' 
                        ? 'bg-blue-100 text-blue-700' 
                        : 'bg-gray-100 text-gray-700'
                    }`}>
                      {validationMode === 'llm' ? '🤖 AI Mode' : '📋 Rule Mode'}
                    </span>
                  </div>
                </div>
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
                      {allProcessedResults.slice().reverse().map((result, idx) => {
                        const actualIndex = allProcessedResults.length - 1 - idx;
                        return (
                          <CompactResultTile 
                            key={idx}
                            result={result}
                            onClick={() => setValidateSelectedIndex(actualIndex)}
                            isSelected={validateSelectedIndex === actualIndex}
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
                    />
                  </div>
                </div>
              </div>
            </motion.div>
          )}

          {/* Bulk Upload View */}
          {activeView === 'bulk' && (
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
          )}

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
                    {allProcessedResults.map((result, idx) => (
                      <CompactResultTile
                        key={idx}
                        result={result}
                        onClick={() => handleResultClick(idx)}
                        isSelected={selectedResultIndex === idx}
                      />
                    ))}
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
              className="grid grid-cols-4 gap-4"
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

              <div className="bg-white rounded-md border border-gray-200 p-4">
                <ChartBarIcon className="h-8 w-8 text-purple-500 mb-2" />
                <p className="text-xs text-gray-600">Batch Jobs</p>
                <p className="text-2xl font-bold text-purple-600">
                  {globalStats?.completed_jobs || 1}
                </p>
              </div>

              {/* Session Stats */}
              <div className="col-span-4 bg-white rounded-md border border-gray-200 p-4">
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