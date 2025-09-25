// Central configuration for the application
export const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Check if we're using ngrok (URL contains 'ngrok')
export const IS_NGROK = API_URL.includes('ngrok');

// Helper function to get headers with ngrok skip if needed
export const getHeaders = (additionalHeaders = {}) => {
  const headers = { ...additionalHeaders };
  if (IS_NGROK) {
    headers['ngrok-skip-browser-warning'] = 'true';
  }
  return headers;
};