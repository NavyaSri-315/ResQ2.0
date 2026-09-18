from flask import Flask, render_template, request, jsonify
from ai_engine import calculate_priority

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('citizen.html')

@app.route('/citizen')
def citizen():
    return render_template('citizen.html')

@app.route('/shelter')
def shelter():
    return render_template('shelter.html')

@app.route('/rescue')
def rescue():
    return render_template('rescue.html')

@app.route('/control')
def control():
    return render_template('control.html')

# API Route to handle incoming citizen emergency requests
@app.route('/api/report-emergency', methods=['POST'])
def report_emergency():
    data = request.json or request.form
    
    req_type = data.get('emergency_type', 'Rescue Needed')
    vulnerability = data.get('vulnerability', 'Standard')
    people_count = int(data.get('people_count', 1))
    location = data.get('location', 'Unknown')
    description = data.get('description', '')

    # Call AI engine to calculate dynamic priority score and explanation
    priority_score, explanation = calculate_priority(req_type, vulnerability, people_count)

    response = {
        "status": "success",
        "message": "Distress signal received and prioritized.",
        "request_details": {
            "type": req_type,
            "location": location,
            "priority_score": priority_score,
            "explanation": explanation
        }
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True, port=5000)