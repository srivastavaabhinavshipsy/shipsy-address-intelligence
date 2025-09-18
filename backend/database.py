"""
SQLite database module for storing address validations and confirmations
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import os

class AddressDatabase:
    def __init__(self, db_path='address_validation.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create validated_addresses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS validated_addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                virtual_number TEXT UNIQUE NOT NULL,
                original_address TEXT NOT NULL,
                normalized_address TEXT,
                confidence_score REAL,
                confidence_level TEXT,
                coordinates TEXT,  -- JSON string
                issues TEXT,  -- JSON array
                suggestions TEXT,  -- JSON array
                components TEXT,  -- JSON object
                contact_number TEXT,
                validation_method TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create confirmed_addresses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS confirmed_addresses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                virtual_number TEXT UNIQUE NOT NULL,
                confirmed_address TEXT,
                confirmed_coordinates TEXT,  -- JSON string
                confirmation_method TEXT,  -- 'call' or 'whatsapp'
                confirmed_by TEXT,
                agent_response TEXT,  -- Full JSON response from polling API
                differences TEXT,  -- JSON object showing what changed
                confirmed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (virtual_number) REFERENCES validated_addresses(virtual_number)
            )
        ''')
        
        # Create agent_calls table to track agent interactions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                virtual_number TEXT NOT NULL,
                action_type TEXT NOT NULL,  -- 'call' or 'whatsapp'
                reference_number TEXT NOT NULL,  -- Same as virtual_number for our case
                phone_number TEXT NOT NULL,
                issues_sent TEXT,  -- JSON array
                api_response TEXT,  -- JSON response from Shipsy
                status TEXT DEFAULT 'pending',  -- 'pending', 'completed', 'failed'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (virtual_number) REFERENCES validated_addresses(virtual_number)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_validated_address(self, data: Dict) -> bool:
        """Save a validated address to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO validated_addresses 
                (virtual_number, original_address, normalized_address, confidence_score,
                 confidence_level, coordinates, issues, suggestions, components,
                 contact_number, validation_method, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                data.get('id'),  # virtual_number
                data.get('original_address'),
                data.get('normalized_address'),
                data.get('confidence_score'),
                data.get('confidence_level'),
                json.dumps(data.get('coordinates')) if data.get('coordinates') else None,
                json.dumps(data.get('issues')) if data.get('issues') else None,
                json.dumps(data.get('suggestions')) if data.get('suggestions') else None,
                json.dumps(data.get('components')) if data.get('components') else None,
                data.get('contact_number'),
                data.get('validation_method')
            ))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving validated address: {e}")
            return False
        finally:
            conn.close()
    
    def save_agent_call(self, data: Dict) -> bool:
        """Save agent call interaction"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO agent_calls 
                (virtual_number, action_type, reference_number, phone_number,
                 issues_sent, api_response, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('virtual_number'),
                data.get('action_type'),
                data.get('reference_number'),
                data.get('phone_number'),
                json.dumps(data.get('issues_sent')) if data.get('issues_sent') else None,
                json.dumps(data.get('api_response')) if data.get('api_response') else None,
                data.get('status', 'pending')
            ))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving agent call: {e}")
            return False
        finally:
            conn.close()
    
    def save_confirmed_address(self, data: Dict) -> bool:
        """Save confirmed address from polling API"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO confirmed_addresses 
                (virtual_number, confirmed_address, confirmed_coordinates,
                 confirmation_method, confirmed_by, agent_response, differences, confirmed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('virtual_number'),
                data.get('confirmed_address'),
                json.dumps(data.get('confirmed_coordinates')) if data.get('confirmed_coordinates') else None,
                data.get('confirmation_method'),
                data.get('confirmed_by'),
                json.dumps(data.get('agent_response')) if data.get('agent_response') else None,
                json.dumps(data.get('differences')) if data.get('differences') else None,
                data.get('confirmed_at', datetime.now().isoformat())
            ))
            
            # Update agent_calls status to completed
            cursor.execute('''
                UPDATE agent_calls 
                SET status = 'completed' 
                WHERE virtual_number = ?
            ''', (data.get('virtual_number'),))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving confirmed address: {e}")
            return False
        finally:
            conn.close()
    
    def get_confirmed_address(self, virtual_number: str) -> Optional[Dict]:
        """Get confirmed address by virtual number"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM confirmed_addresses 
                WHERE virtual_number = ?
            ''', (virtual_number,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'virtual_number': row['virtual_number'],
                    'confirmed_address': row['confirmed_address'],
                    'confirmed_coordinates': json.loads(row['confirmed_coordinates']) if row['confirmed_coordinates'] else None,
                    'confirmation_method': row['confirmation_method'],
                    'confirmed_by': row['confirmed_by'],
                    'agent_response': json.loads(row['agent_response']) if row['agent_response'] else None,
                    'differences': json.loads(row['differences']) if row['differences'] else None,
                    'confirmed_at': row['confirmed_at'],
                    'status': 'confirmed'
                }
            return None
        except Exception as e:
            print(f"Error getting confirmed address: {e}")
            return None
        finally:
            conn.close()
    
    def get_pending_confirmations(self) -> List[str]:
        """Get list of virtual numbers pending confirmation"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT DISTINCT ac.virtual_number 
                FROM agent_calls ac
                LEFT JOIN confirmed_addresses ca ON ac.virtual_number = ca.virtual_number
                WHERE ca.virtual_number IS NULL
            ''')
            # Returns all CNs where agent was triggered but no confirmed address yet
            # Doesn't rely on status field in case of any edge cases
            
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting pending confirmations: {e}")
            return []
        finally:
            conn.close()
    
    def get_all_addresses(self) -> List[Dict]:
        """Get all validated addresses with their confirmation status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT 
                    va.*,
                    ca.confirmed_address,
                    ca.confirmed_coordinates,
                    ca.confirmation_method,
                    ca.confirmed_at,
                    ac.action_type as agent_triggered
                FROM validated_addresses va
                LEFT JOIN confirmed_addresses ca ON va.virtual_number = ca.virtual_number
                LEFT JOIN (
                    SELECT DISTINCT virtual_number, action_type 
                    FROM agent_calls 
                    GROUP BY virtual_number
                ) ac ON va.virtual_number = ac.virtual_number
                ORDER BY va.created_at DESC
            ''')
            
            results = []
            for row in cursor.fetchall():
                result = {
                    'virtual_number': row['virtual_number'],
                    'original_address': row['original_address'],
                    'normalized_address': row['normalized_address'],
                    'confidence_score': row['confidence_score'],
                    'confidence_level': row['confidence_level'],
                    'coordinates': json.loads(row['coordinates']) if row['coordinates'] else None,
                    'issues': json.loads(row['issues']) if row['issues'] else None,
                    'suggestions': json.loads(row['suggestions']) if row['suggestions'] else None,
                    'contact_number': row['contact_number'],
                    'validation_method': row['validation_method'],
                    'created_at': row['created_at'],
                    'agent_triggered': bool(row['agent_triggered'])  # True if agent was triggered
                }
                
                # Include confirmed address ONLY if agent was triggered AND it's for this specific CN
                if row['agent_triggered'] and row['confirmed_address']:
                    result['confirmed_address'] = {
                        'address': row['confirmed_address'],
                        'coordinates': json.loads(row['confirmed_coordinates']) if row['confirmed_coordinates'] else None,
                        'confirmation_method': row['confirmation_method'],
                        'confirmed_at': row['confirmed_at']
                    }
                
                results.append(result)
            
            return results
        except Exception as e:
            print(f"Error getting all addresses: {e}")
            return []
        finally:
            conn.close()