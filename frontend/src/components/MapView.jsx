import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { motion } from 'framer-motion';

// Fix for default markers in React
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const MapView = ({ results }) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);

  useEffect(() => {
    // Initialize map only once
    if (!mapInstanceRef.current && mapRef.current) {
      mapInstanceRef.current = L.map(mapRef.current).setView([-28.4793, 24.6727], 5);
      
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18,
      }).addTo(mapInstanceRef.current);
    }

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!mapInstanceRef.current) return;

    // Clear existing markers
    markersRef.current.forEach(marker => marker.remove());
    markersRef.current = [];

    // Add new markers
    if (results && results.length > 0) {
      const bounds = [];
      
      results.forEach(result => {
        if (result.coordinates) {
          const { latitude, longitude } = result.coordinates;
          
          // Create custom icon based on confidence level
          const iconColor = 
            result.confidence_level === 'CONFIDENT' ? '#10B981' :
            result.confidence_level === 'LIKELY' ? '#3B82F6' :
            result.confidence_level === 'SUSPICIOUS' ? '#F59E0B' :
            '#EF4444';
          
          const customIcon = L.divIcon({
            html: `
              <div style="
                background: ${iconColor};
                width: 12px;
                height: 12px;
                border-radius: 50%;
                border: 2px solid white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.3);
              "></div>
            `,
            className: 'custom-marker',
            iconSize: [12, 12],
            iconAnchor: [6, 6],
          });
          
          const marker = L.marker([latitude, longitude], { icon: customIcon })
            .addTo(mapInstanceRef.current)
            .bindPopup(`
              <div style="min-width: 200px;">
                <strong>${result.normalized_address || result.original_address}</strong><br/>
                <span style="color: ${iconColor}; font-weight: bold;">
                  ${result.confidence_level} (${result.confidence_score}%)
                </span>
                ${result.issues.length > 0 ? 
                  `<br/><small style="color: #ef4444;">Issues: ${result.issues.length}</small>` : 
                  ''}
              </div>
            `);
          
          markersRef.current.push(marker);
          bounds.push([latitude, longitude]);
        }
      });

      // Fit map to show all markers
      if (bounds.length > 0) {
        mapInstanceRef.current.fitBounds(bounds, { padding: [50, 50] });
      }
    } else {
      // Reset to South Africa view if no results
      mapInstanceRef.current.setView([-28.4793, 24.6727], 5);
    }
  }, [results]);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-white rounded-lg shadow-sm border border-shipsy-border overflow-hidden flex-1"
    >
      <div 
        ref={mapRef} 
        className="w-full h-full"
        style={{ minHeight: '400px', zIndex: 1 }}
      />
    </motion.div>
  );
};

export default MapView;