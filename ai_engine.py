import math

def haversine(lat1, lon1, lat2, lon2):
    """Distance in km between two coordinates"""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
         math.sin(dlon/2)**2)
    return R * 2 * math.asin(math.sqrt(a))


def calculate_priority(request):
    """Multi-factor priority scoring. Returns score + factors + explanation."""
    
    urgency_map = {
        'life_threatening': 10, 'rescue': 9, 'medical': 8,
        'shelter': 5, 'food': 4
    }
    urgency = urgency_map.get(request.get('type', 'rescue'), 5)
    
    people = min(request.get('people', 1) * 2, 10)
    
    vuln_map = {'elderly': 3, 'disabled': 4, 'children': 2, 'pregnant': 4, 'injured': 3}
    vulnerability = min(sum(vuln_map.get(v, 0) for v in request.get('vulnerability', [])), 10)
    
    time_sensitivity = 8
    
    confidence_map = {'app': 9, 'sms': 6, 'ivr': 5, 'proxy': 7}
    confidence = confidence_map.get(request.get('source', 'app'), 7)
    
    accessibility = 8
    
    weights = {
        'urgency': 0.30, 'people': 0.15, 'vulnerability': 0.20,
        'time_sensitivity': 0.15, 'confidence': 0.10, 'accessibility': 0.10
    }
    
    score = (
        urgency * weights['urgency'] +
        people * weights['people'] +
        vulnerability * weights['vulnerability'] +
        time_sensitivity * weights['time_sensitivity'] +
        confidence * weights['confidence'] +
        accessibility * weights['accessibility']
    )
    
    return {
        'score': round(score, 2),
        'factors': {
            'urgency': {'value': request.get('type'), 'score': urgency, 'weight': weights['urgency']},
            'people': {'value': request.get('people'), 'score': people, 'weight': weights['people']},
            'vulnerability': {'value': request.get('vulnerability', []), 'score': vulnerability, 'weight': weights['vulnerability']},
            'time_sensitivity': {'value': 'high', 'score': time_sensitivity, 'weight': weights['time_sensitivity']},
            'confidence': {'value': request.get('source', 'app'), 'score': confidence, 'weight': weights['confidence']},
            'accessibility': {'value': 'reachable', 'score': accessibility, 'weight': weights['accessibility']}
        },
        'explanation': f"Priority {round(score,2)}/10 — {request.get('type')}, {request.get('people')} people, vulnerability: {request.get('vulnerability', [])}"
    }


def recommend_resource(request, resources):
    """Score all available resources for a request. Return best + alternatives."""
    
    if not resources:
        return {
            'recommended': None,
            'alternatives': [],
            'explanation': 'No available resources'
        }
    
    scores = []
    for r in resources:
        if r.get('status') != 'available':
            continue
        
        required = request.get('type', 'rescue')
        caps = r.get('capabilities', [])
        capability = 10 if required in caps else 0
        
        dist = haversine(r['lat'], r['lng'], request['lat'], request['lng'])
        proximity = max(0, 10 - (dist / 5))
        
        avail = r.get('capacity_total', 0) - r.get('capacity_used', 0)
        capacity = 10 if avail >= request.get('people', 1) else 0
        
        reliability = r.get('reliability', 0.9) * 10
        
        eta = (dist / 30) * 60
        eta_score = max(0, 10 - (eta / 10))
        
        weights = {'capability': 0.30, 'proximity': 0.25, 'capacity': 0.15,
                   'reliability': 0.10, 'eta': 0.20}
        
        score = (
            capability * weights['capability'] +
            proximity * weights['proximity'] +
            capacity * weights['capacity'] +
            reliability * weights['reliability'] +
            eta_score * weights['eta']
        )
        
        scores.append({
            'resource_id': r['id'],
            'resource_name': r['name'],
            'score': round(score, 2),
            'distance_km': round(dist, 2),
            'eta_minutes': round(eta, 1),
            'factors': {
                'capability': {'value': required, 'score': capability, 'weight': weights['capability']},
                'proximity': {'value': f"{round(dist,2)} km", 'score': round(proximity,2), 'weight': weights['proximity']},
                'capacity': {'value': f"{avail}/{r.get('capacity_total')}", 'score': capacity, 'weight': weights['capacity']},
                'reliability': {'value': r.get('reliability', 0.9), 'score': round(reliability,2), 'weight': weights['reliability']},
                'eta': {'value': f"{round(eta,1)} min", 'score': round(eta_score,2), 'weight': weights['eta']}
            }
        })
    
    scores.sort(key=lambda x: x['score'], reverse=True)
    
    if not scores:
        return {'recommended': None, 'alternatives': [], 'explanation': 'No suitable resources'}
    
    best = scores[0]
    alternatives = []
    for alt in scores[1:4]:
        reason = []
        if alt['score'] < best['score']:
            reason.append(f"lower score ({alt['score']})")
        if alt['distance_km'] > best['distance_km']:
            reason.append(f"farther ({alt['distance_km']} km)")
        alternatives.append({
            'resource_id': alt['resource_id'],
            'resource_name': alt['resource_name'],
            'score': alt['score'],
            'reason_rejected': ', '.join(reason) if reason else 'not selected'
        })
    
    return {
        'recommended': best,
        'alternatives': alternatives,
        'explanation': f"{best['resource_name']} selected (score {best['score']}/10). Distance: {best['distance_km']} km, ETA: {best['eta_minutes']} min."
    }


def match_missing_person(missing, found_list):
    """Match a missing person against found persons."""
    matches = []
    
    for f in found_list:
        name_sim = 0
        if missing['name'].lower() == f['name'].lower():
            name_sim = 1.0
        elif missing['name'].lower() in f['name'].lower() or f['name'].lower() in missing['name'].lower():
            name_sim = 0.7
        else:
            # Simple character overlap
            m_set = set(missing['name'].lower())
            f_set = set(f['name'].lower())
            if m_set and f_set:
                overlap = len(m_set & f_set) / max(len(m_set), len(f_set))
                name_sim = round(overlap * 0.6, 2)
        
        age_match = 1.0 if abs(missing['age'] - f['age']) <= 2 else 0.3
        gender_match = 1.0 if missing['gender'].lower() == f['gender'].lower() else 0
        
        confidence = (name_sim * 0.40 + age_match * 0.30 + gender_match * 0.30) * 100
        
        if confidence > 50:
            matches.append({
                'found_id': f['id'],
                'found_name': f['name'],
                'shelter': f.get('shelter', 'Unknown'),
                'confidence': round(confidence, 1),
                'factors': {
                    'name': {'value': f"{missing['name']} vs {f['name']}", 'score': round(name_sim, 2), 'weight': 0.40},
                    'age': {'value': f"{missing['age']} vs {f['age']}", 'score': round(age_match, 2), 'weight': 0.30},
                    'gender': {'value': f"{missing['gender']} vs {f['gender']}", 'score': round(gender_match, 2), 'weight': 0.30}
                }
            })
    
    matches.sort(key=lambda x: x['confidence'], reverse=True)
    
    return {
        'matches': matches,
        'best': matches[0] if matches else None,
        'explanation': f"Found {len(matches)} potential match(es)" if matches else "No matches found"
    }


def check_replan(event, assignments):
    """Check if replanning is needed based on an event."""
    
    if event['type'] == 'road_block':
        affected = [a for a in assignments if a.get('status') in ('assigned', 'en_route')]
        if affected:
            return {
                'needed': True,
                'trigger': 'road_block',
                'affected': affected[:3],
                'old_plan': {'route': 'A → B → C', 'eta': 8},
                'new_plan': {'route': 'A → D → C', 'eta': 14},
                'impact': '+6 min delay',
                'explanation': f"Road blocked at {event.get('location', 'unknown')}. Rerouting via alternate path adds 6 min but avoids blockage.",
                'confidence': 0.92
            }
    
    elif event['type'] == 'new_critical_request':
        new_priority = event.get('priority', 9)
        lower = [a for a in assignments if a.get('priority', 0) < new_priority]
        if lower:
            return {
                'needed': True,
                'trigger': 'new_critical_request',
                'affected': lower[:1],
                'explanation': f"New critical request (priority {new_priority}) can use resource from lower-priority task.",
                'confidence': 0.85
            }
    
    elif event['type'] == 'shelter_full':
        affected = [a for a in assignments if a.get('destination') == event.get('shelter_id')]
        if affected:
            return {
                'needed': True,
                'trigger': 'shelter_full',
                'affected': affected,
                'explanation': f"Shelter {event.get('shelter_id')} is full. Redirecting incoming teams to alternate shelter.",
                'confidence': 0.90
            }
    
    return {'needed': False, 'explanation': 'No replan needed'}


if __name__ == '__main__':
    # Quick test
    req = {'type': 'rescue', 'people': 5, 'vulnerability': ['elderly'], 'source': 'app'}
    print(calculate_priority(req))
    
    resources = [
        {'id': 'BOAT-001', 'name': 'Boat 1', 'status': 'available', 'lat': 20.2961, 'lng': 85.8245,
         'capacity_total': 10, 'capacity_used': 0, 'capabilities': ['rescue'], 'reliability': 0.95}
    ]
    req2 = {'type': 'rescue', 'people': 5, 'lat': 20.30, 'lng': 85.83}
    print(recommend_resource(req2, resources))