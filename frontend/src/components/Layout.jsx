import React from 'react';
import { motion } from 'framer-motion';

const Layout = ({ children, stats }) => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-shipsy-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-3">
            <motion.div 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center space-x-4"
            >
              <img 
                src="https://shipsy-public-assets.s3.amazonaws.com/shipsyflamingo/logo.png" 
                alt="Shipsy" 
                className="h-8"
              />
              <div className="border-l border-shipsy-border pl-4">
                <h1 className="text-lg font-semibold text-shipsy-darkGray">
                  Address Intelligence
                </h1>
                <p className="text-xs text-shipsy-gray">Address Intelligence System</p>
              </div>
            </motion.div>

            {/* Stats Badges */}
            <motion.div 
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="hidden md:flex items-center space-x-3"
            >
              <div className="text-right">
                <p className="text-xs text-shipsy-gray">Validated</p>
                <p className="text-sm font-semibold text-shipsy-darkGray">{stats?.total_validated || 0}</p>
              </div>
              
              <div className="text-right">
                <p className="text-xs text-shipsy-gray">Success Rate</p>
                <p className="text-sm font-semibold text-success">{stats?.success_rate || 0}%</p>
              </div>
            </motion.div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>
    </div>
  );
};

export default Layout;