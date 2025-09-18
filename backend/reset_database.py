#!/usr/bin/env python3
"""
Script to reset the database and start fresh
"""

import os
import json

def reset_database():
    """Clear all data from database tables"""
    import sqlite3
    
    db_file = 'address_validation.db'
    
    if os.path.exists(db_file):
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Clear all tables
            tables_to_clear = [
                'validated_addresses',
                'confirmed_addresses', 
                'agent_calls'
            ]
            
            for table in tables_to_clear:
                cursor.execute(f"DELETE FROM {table}")
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")  # Reset auto-increment
                print(f"✅ Cleared table: {table}")
            
            conn.commit()
            
            # Show counts to confirm
            for table in tables_to_clear:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   {table}: {count} records")
            
            conn.close()
            print("✅ All database tables cleared successfully")
            
        except Exception as e:
            print(f"❌ Error clearing database: {e}")
    else:
        print(f"ℹ️  No existing database found")
    
    print("✅ Database is now empty and ready for fresh data")

def reset_virtual_numbers():
    """Reset virtual numbers to start from CRNSEP001"""
    
    # Generate full list from CRNSEP001 to CRNSEP1000
    virtual_numbers = []
    for i in range(1, 1001):
        virtual_numbers.append(f"CRNSEP{i:03d}")  # Format with leading zeros
    
    # Save to file
    with open('virtual_numbers.json', 'w') as f:
        json.dump(virtual_numbers, f, indent=2)
    
    print(f"✅ Reset virtual numbers: CRNSEP001 to CRNSEP1000")
    print(f"📝 Total {len(virtual_numbers)} virtual numbers available")

def main():
    print("🔄 Resetting Address Validation System...")
    print("-" * 40)
    
    # Reset database
    reset_database()
    
    # Reset virtual numbers
    reset_virtual_numbers()
    
    print("-" * 40)
    print("✨ System reset complete!")
    print("🚀 Ready to start fresh with real data")

if __name__ == "__main__":
    main()