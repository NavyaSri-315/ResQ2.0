import sqlite3
import json
from datetime import datetime

DB_NAME = 'disaster.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, phone TEXT, role TEXT,
        language TEXT DEFAULT 'en',
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT, people INTEGER, description TEXT,
        lat REAL, lng REAL, floor TEXT, landmark TEXT,
        vulnerability TEXT,
        priority REAL, factors TEXT,
        status TEXT DEFAULT 'pending',
        source TEXT DEFAULT 'app',
        created_at TEXT, updated_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS resources (
        id TEXT PRIMARY KEY,
        type TEXT, name TEXT,
        status TEXT DEFAULT 'available',
        lat REAL, lng REAL,
        capacity_total INTEGER, capacity_used INTEGER DEFAULT 0,
        capabilities TEXT, reliability REAL DEFAULT 0.9,
        last_ping TEXT, created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER, resource_id TEXT,
        status TEXT DEFAULT 'assigned',
        eta INTEGER, match_score REAL, explanation TEXT,
        assigned_at TEXT, completed_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS shelters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, type TEXT,
        lat REAL, lng REAL,
        capacity_total INTEGER, capacity_used INTEGER DEFAULT 0,
        facilities TEXT, contact TEXT,
        status TEXT DEFAULT 'open',
        updated_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS missing_persons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reported_by INTEGER,
        name TEXT, age INTEGER, gender TEXT,
        photo_url TEXT, last_seen TEXT, description TEXT,
        status TEXT DEFAULT 'missing',
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS found_persons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shelter_id INTEGER,
        name TEXT, age INTEGER, gender TEXT,
        photo_url TEXT, condition TEXT,
        found_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        missing_id INTEGER, found_id INTEGER,
        confidence REAL, factors TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS road_blocks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lat REAL, lng REAL, description TEXT,
        reported_by INTEGER, created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, action TEXT, entity TEXT,
        entity_id INTEGER, details TEXT, created_at TEXT
    )''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

def seed_data():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM resources')
    if c.fetchone()[0] > 0:
        print("ℹ️ Data already seeded")
        conn.close()
        return
    
    now = datetime.now().isoformat()
    
    # Resources (near Bhubaneswar for demo)
    resources = [
        ('BOAT-001', 'boat', 'Rescue Boat Alpha', 'available', 20.2961, 85.8245, 10, 0, '["rescue"]', 0.95, now, now),
        ('BOAT-002', 'boat', 'Rescue Boat Beta', 'available', 20.3010, 85.8300, 8, 0, '["rescue"]', 0.90, now, now),
        ('AMB-001', 'ambulance', 'Ambulance 1', 'available', 20.2900, 85.8200, 4, 0, '["medical"]', 0.92, now, now),
        ('AMB-002', 'ambulance', 'Ambulance 2', 'available', 20.3050, 85.8350, 4, 0, '["medical"]', 0.88, now, now),
        ('TEAM-001', 'team', 'NDRF Team 1', 'available', 20.2950, 85.8250, 15, 0, '["rescue", "medical"]', 0.97, now, now),
        ('HELI-001', 'helicopter', 'Helicopter 1', 'available', 20.2800, 85.8100, 6, 0, '["rescue", "medical"]', 0.93, now, now),
    ]
    c.executemany('INSERT INTO resources (id, type, name, status, lat, lng, capacity_total, capacity_used, capabilities, reliability, last_ping, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', resources)
    
    # Shelters
    shelters = [
        ('Shelter A', 'shelter', 20.2980, 85.8280, 100, 45, '["food", "water", "medical"]', '9999000001', 'open', now),
        ('Shelter B', 'shelter', 20.3050, 85.8400, 80, 30, '["food", "water"]', '9999000002', 'open', now),
        ('City Hospital', 'hospital', 20.2920, 85.8150, 200, 120, '["medical", "surgery", "icu"]', '9999000003', 'open', now),
    ]
    c.executemany('INSERT INTO shelters (name, type, lat, lng, capacity_total, capacity_used, facilities, contact, status, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)', shelters)
    
    # Missing persons
    missing = [
        (1, 'Ravi Kumar', 8, 'M', None, 'Near Temple, Zone A', 'Wearing blue shirt', 'missing', now),
        (1, 'Priya Sharma', 35, 'F', None, 'Zone B, House 42', 'Last seen near river', 'missing', now),
        (1, 'Amit Das', 12, 'M', None, 'Zone A, School', 'Separated during evacuation', 'missing', now),
        (1, 'Sunita Patel', 60, 'F', None, 'Zone C', 'Elderly, may be confused', 'missing', now),
        (1, 'Kiran Behera', 25, 'M', None, 'Zone B', 'Wearing red jacket', 'missing', now),
    ]
    c.executemany('INSERT INTO missing_persons (reported_by, name, age, gender, photo_url, last_seen, description, status, created_at) VALUES (?,?,?,?,?,?,?,?,?)',
                  [(m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7], m[8]) for m in missing])
    
    # Found persons
    found = [
        (1, 'Ravi Kumr', 8, 'M', None, 'stable', now),
        (2, 'Priya Sharma', 35, 'F', None, 'stable', now),
        (1, 'Unknown Boy', 10, 'M', None, 'stable', now),
    ]
    c.executemany('INSERT INTO found_persons (shelter_id, name, age, gender, photo_url, condition, found_at) VALUES (?,?,?,?,?,?,?)', found)
    
    conn.commit()
    conn.close()
    print(f"✅ Seeded {len(resources)} resources, {len(shelters)} shelters, {len(missing)} missing, {len(found)} found")

if __name__ == '__main__':
    init_db()
    seed_data()