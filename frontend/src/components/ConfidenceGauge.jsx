import React from 'react';
import { motion } from 'framer-motion';

const ConfidenceGauge = ({ score, level }) => {
  const getColor = () => {
    if (score >= 90) return '#10B981'; // green
    if (score >= 70) return '#3B82F6'; // blue
    if (score >= 50) return '#F59E0B'; // amber
    return '#EF4444'; // red
  };

  const getEmoji = () => {
    if (score >= 90) return '✅';
    if (score >= 70) return '👍';
    if (score >= 50) return '⚠️';
    return '❌';
  };

  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="relative">
      <svg className="w-32 h-32 transform -rotate-90">
        {/* Background circle */}
        <circle
          cx="64"
          cy="64"
          r="45"
          stroke="currentColor"
          strokeWidth="8"
          fill="none"
          className="text-gray-200"
        />
        
        {/* Progress circle */}
        <motion.circle
          cx="64"
          cy="64"
          r="45"
          stroke={getColor()}
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset }}
          transition={{ duration: 1.5, ease: "easeOut" }}
        />
      </svg>
      
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.5, type: "spring" }}
          className="text-3xl"
        >
          {getEmoji()}
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
          className="text-center"
        >
          <p className="text-2xl font-bold" style={{ color: getColor() }}>
            {score}%
          </p>
          <p className="text-xs text-gray-600 uppercase tracking-wider">
            {level}
          </p>
        </motion.div>
      </div>
    </div>
  );
};

export default ConfidenceGauge;