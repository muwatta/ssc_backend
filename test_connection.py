#!/usr/bin/env python
import os
import sys
from pathlib import Path

# Setup Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection
from decouple import config

print("Testing database connection...")
print(f"Database URL: {config('DATABASE_URL')[:50]}...")

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Connected! PostgreSQL version: {version[0][:50]}...")
        
        # Check if our tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"\n📊 Found {len(tables)} tables:")
        for table in tables[:10]:  # Show first 10
            print(f"   - {table[0]}")
            
except Exception as e:
    print(f"❌ Connection failed: {e}")