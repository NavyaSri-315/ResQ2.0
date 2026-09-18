from flask import Flask, render_template, request, jsonify
import sqlite3
import json
from datetime import datetime

from database import init_db, seed_data, get_db
from ai_engine import calculate_priority, recommend_resource, match_missing_person, check_replan

app = Flask(__name__)


# ---------- PAGES ----------
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/citizen')
def citizen():
    return render_template('citizen.html')

@app.route('/control')
def control():
    return render_template('control.html')

@app.route('/rescue')
def rescue():
    return render_template('rescue.html')

@app.route('/shelter')
def shelter():
    return render_template('shelter.html')

@app.route('/simulation')
def simulation():
    return render_template('simulation.html')


# ---------- REQUESTS ----------
@app.route('/api/requests', methods=['GET', 'POST'])
def requests_api():
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        priority = calculate_priority(data)
        now = datetime.now().isoformat()
        
        c.execute('''INSERT INTO requests 
            (user_id, type, people, description, lat, lng, floor, landmark,
             vulnerability, priority, factors, source, status, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (data.get('user_id', 1), data.get('type'), data.get('people', 1),
             data.get('description', ''), data.get('lat'), data.get('lng'),
             data.get('floor', ''), data.get('landmark', ''),
             json.dumps(data.get('vulnerability', [])),
             priority['score'], json.dumps(priority['factors']),
             data.get('source', 'app'), 'pending', now, now))
        
        conn.commit()
        req_id = c.lastrowid
        conn.close()
        
        return jsonify({
            'id': req_id,
            'priority': priority['score'],
            'factors': priority['factors'],
            'explanation': priority['explanation']
        })
    
    c.execute('SELECT * FROM requests ORDER BY priority DESC')
    rows = c.fetchall()
    conn.close()
    
    result = []
    for r in rows:
        result.append({
            'id': r['id'], 'type': r['type'], 'people': r['people'],
            'description': r['description'], 'lat': r['lat'], 'lng': r['lng'],
            'floor': r['floor'], 'landmark': r['landmark'],
            'vulnerability': json.loads(r['vulnerability']) if r['vulnerability'] else [],
            'priority': r['priority'],
            'factors': json.loads(r['factors']) if r['factors'] else {},
            'status': r['status'], 'source': r['source'],
            'created_at': r['created_at']
        })
    return jsonify(result)


@app.route('/api/requests/<int:req_id>')
def get_request(req_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM requests WHERE id = ?', (req_id,))
    r = c.fetchone()
    conn.close()
    if not r:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': r['id'], 'type': r['type'], 'people': r['people'],
        'lat': r['lat'], 'lng': r['lng'],
        'vulnerability': json.loads(r['vulnerability']) if r['vulnerability'] else [],
        'priority': r['priority'], 'status': r['status']
    })


@app.route('/api/requests/<int:req_id>', methods=['PATCH'])
def update_request(req_id):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE requests SET status = ?, updated_at = ? WHERE id = ?',
              (data.get('status'), datetime.now().isoformat(), req_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


# ---------- RESOURCES ----------
@app.route('/api/resources')
def resources_api():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM resources')
    rows = c.fetchall()
    conn.close()
    
    result = []
    for r in rows:
        result.append({
            'id': r['id'], 'type': r['type'], 'name': r['name'],
            'status': r['status'], 'lat': r['lat'], 'lng': r['lng'],
            'capacity_total': r['capacity_total'], 'capacity_used': r['capacity_used'],
            'capabilities': json.loads(r['capabilities']) if r['capabilities'] else [],
            'reliability': r['reliability']
        })
    return jsonify(result)


@app.route('/api/resources/available')
def available_resources():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM resources WHERE status = "available"')
    rows = c.fetchall()
    conn.close()
    
    result = []
    for r in rows:
        result.append({
            'id': r['id'], 'type': r['type'], 'name': r['name'],
            'status': r['status'], 'lat': r['lat'], 'lng': r['lng'],
            'capacity_total': r['capacity_total'], 'capacity_used': r['capacity_used'],
            'capabilities': json.loads(r['capabilities']) if r['capabilities'] else [],
            'reliability': r['reliability']
        })
    return jsonify(result)


# ---------- RECOMMENDATION ----------
@app.route('/api/recommend/<int:request_id>')
def recommend(request_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM requests WHERE id = ?', (request_id,))
    req = c.fetchone()
    if not req:
        conn.close()
        return jsonify({'error': 'Request not found'}), 404
    
    c.execute('SELECT * FROM resources WHERE status = "available"')
    rows = c.fetchall()
    conn.close()
    
    request_data = {
        'id': req['id'], 'type': req['type'], 'people': req['people'],
        'lat': req['lat'], 'lng': req['lng']
    }
    
    resource_list = []
    for r in rows:
        resource_list.append({
            'id': r['id'], 'type': r['type'], 'name': r['name'],
            'status': r['status'], 'lat': r['lat'], 'lng': r['lng'],
            'capacity_total': r['capacity_total'], 'capacity_used': r['capacity_used'],
            'capabilities': json.loads(r['capabilities']) if r['capabilities'] else [],
            'reliability': r['reliability']
        })
    
    result = recommend_resource(request_data, resource_list)
    return jsonify(result)


# ---------- ASSIGN ----------
@app.route('/api/assign', methods=['POST'])
def assign():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    now = datetime.now().isoformat()
    
    c.execute('''INSERT INTO assignments 
        (request_id, resource_id, status, eta, match_score, explanation, assigned_at)
        VALUES (?,?,?,?,?,?,?)''',
        (data['request_id'], data['resource_id'], 'assigned',
         data.get('eta', 10), data.get('score', 0),
         data.get('explanation', ''), now))
    
    c.execute('UPDATE requests SET status = "assigned", updated_at = ? WHERE id = ?',
              (now, data['request_id']))
    c.execute('UPDATE resources SET status = "assigned" WHERE id = ?',
              (data['resource_id'],))
    
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


@app.route('/api/assignments')
def get_assignments():
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT a.*, r.name as resource_name, r.type as resource_type,
                 r.lat as resource_lat, r.lng as resource_lng,
                 q.type as request_type, q.people, q.lat as request_lat,
                 q.lng as request_lng, q.priority
                 FROM assignments a
                 JOIN resources r ON a.resource_id = r.id
                 JOIN requests q ON a.request_id = q.id
                 ORDER BY a.assigned_at DESC''')
    rows = c.fetchall()
    conn.close()
    
    result = []
    for r in rows:
        result.append({
            'id': r['id'], 'request_id': r['request_id'],
            'resource_id': r['resource_id'], 'resource_name': r['resource_name'],
            'resource_type': r['resource_type'],
            'resource_lat': r['resource_lat'], 'resource_lng': r['resource_lng'],
            'request_type': r['request_type'], 'people': r['people'],
            'request_lat': r['request_lat'], 'request_lng': r['request_lng'],
            'priority': r['priority'], 'status': r['status'],
            'eta': r['eta'], 'match_score': r['match_score'],
            'explanation': r['explanation']
        })
    return jsonify(result)


# ---------- SHELTERS ----------
@app.route('/api/shelters')
def shelters_api():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM shelters')
    rows = c.fetchall()
    conn.close()
    
    result = []
    for r in rows:
        result.append({
            'id': r['id'], 'name': r['name'], 'type': r['type'],
            'lat': r['lat'], 'lng': r['lng'],
            'capacity_total': r['capacity_total'], 'capacity_used': r['capacity_used'],
            'facilities': json.loads(r['facilities']) if r['facilities'] else [],
            'contact': r['contact'], 'status': r['status']
        })
    return jsonify(result)


@app.route('/api/shelters/<int:shelter_id>/capacity', methods=['PATCH'])
def update_capacity(shelter_id):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute('''UPDATE shelters SET capacity_total = ?, capacity_used = ?,
                 facilities = ?, status = ?, updated_at = ? WHERE id = ?''',
              (data.get('capacity_total'), data.get('capacity_used'),
               json.dumps(data.get('facilities', [])),
               data.get('status', 'open'), datetime.now().isoformat(), shelter_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


# ---------- MISSING PERSONS ----------
@app.route('/api/missing', methods=['GET', 'POST'])
def missing_api():
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO missing_persons 
            (reported_by, name, age, gender, last_seen, description, status, created_at)
            VALUES (?,?,?,?,?,?,?,?)''',
            (data.get('reported_by', 1), data['name'], data['age'],
             data['gender'], data.get('last_seen', ''),
             data.get('description', ''), 'missing',
             datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({'status': 'ok'})
    
    c.execute('SELECT * FROM missing_persons ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    return jsonify([{
        'id': r['id'], 'name': r['name'], 'age': r['age'],
        'gender': r['gender'], 'last_seen': r['last_seen'],
        'description': r['description'], 'status': r['status'],
        'created_at': r['created_at']
    } for r in rows])


@app.route('/api/missing/<int:mid>')
def get_missing(mid):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM missing_persons WHERE id = ?', (mid,))
    r = c.fetchone()
    conn.close()
    if not r:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': r['id'], 'name': r['name'], 'age': r['age'],
        'gender': r['gender'], 'last_seen': r['last_seen'],
        'description': r['description'], 'status': r['status']
    })


# ---------- FOUND PERSONS ----------
@app.route('/api/found', methods=['GET', 'POST'])
def found_api():
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute('''INSERT INTO found_persons 
            (shelter_id, name, age, gender, condition, found_at)
            VALUES (?,?,?,?,?,?)''',
            (data.get('shelter_id', 1), data['name'], data['age'],
             data['gender'], data.get('condition', 'stable'),
             datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({'status': 'ok'})
    
    c.execute('''SELECT f.*, s.name as shelter_name 
                 FROM found_persons f
                 LEFT JOIN shelters s ON f.shelter_id = s.id''')
    rows = c.fetchall()
    conn.close()
    return jsonify([{
        'id': r['id'], 'name': r['name'], 'age': r['age'],
        'gender': r['gender'], 'shelter': r['shelter_name'] or 'Unknown',
        'condition': r['condition']
    } for r in rows])


# ---------- MATCH ----------
@app.route('/api/match/<int:missing_id>')
def match(missing_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM missing_persons WHERE id = ?', (missing_id,))
    missing = c.fetchone()
    if not missing:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
    
    c.execute('''SELECT f.*, s.name as shelter_name 
                 FROM found_persons f
                 LEFT JOIN shelters s ON f.shelter_id = s.id''')
    rows = c.fetchall()
    conn.close()
    
    missing_data = {'name': missing['name'], 'age': missing['age'], 'gender': missing['gender']}
    found_list = [{
        'id': r['id'], 'name': r['name'], 'age': r['age'],
        'gender': r['gender'], 'shelter': r['shelter_name'] or 'Unknown'
    } for r in rows]
    
    result = match_missing_person(missing_data, found_list)
    return jsonify(result)


# ---------- ROAD BLOCKS ----------
@app.route('/api/road-block', methods=['POST'])
def road_block():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO road_blocks (lat, lng, description, reported_by, created_at)
                 VALUES (?,?,?,?,?)''',
              (data['lat'], data['lng'], data.get('description', ''),
               1, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    # Trigger replan check
    event = {'type': 'road_block', 'location': data.get('description', 'unknown')}
    replan = check_replan(event, [])
    
    return jsonify({
        'status': 'ok',
        'message': 'Road block added. Replan triggered.',
        'replan': replan
    })


@app.route('/api/road-blocks')
def get_road_blocks():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM road_blocks')
    rows = c.fetchall()
    conn.close()
    return jsonify([{
        'id': r['id'], 'lat': r['lat'], 'lng': r['lng'],
        'description': r['description'], 'created_at': r['created_at']
    } for r in rows])


# ---------- METRICS ----------
@app.route('/api/metrics')
def metrics():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM requests')
    total_requests = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM requests WHERE status = "assigned"')
    assigned = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM resources WHERE status = "available"')
    available = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM resources')
    total_resources = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM missing_persons')
    total_missing = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM found_persons')
    total_found = c.fetchone()[0]
    
    conn.close()
    
    utilization = round((total_resources - available) / total_resources * 100, 1) if total_resources else 0
    
    return jsonify({
        'total_requests': total_requests,
        'assigned_requests': assigned,
        'available_resources': available,
        'total_resources': total_resources,
        'resource_utilization': utilization,
        'total_missing': total_missing,
        'total_found': total_found,
        'match_rate': round(total_found / total_missing * 100, 1) if total_missing else 0
    })


# ---------- START ----------
if __name__ == '__main__':
    init_db()
    seed_data()
    print("🚀 Server running at http://localhost:5000")
    app.run(debug=True, port=5000)