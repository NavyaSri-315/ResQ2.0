def calculate_priority(emergency_type, vulnerability, people_count):
    """
    Calculates a dynamic priority score based on PS-2 constraints:
    Urgency, affected people count, and vulnerability status.
    """
    score = 0

    # Base score by emergency urgency
    urgency_weights = {
        "Medical Emergency": 50,
        "Rescue Needed": 40,
        "Fire Hazard": 35,
        "Food & Water Crisis": 20
    }
    score += urgency_weights.get(emergency_type, 10)

    # Vulnerability multiplier
    vulnerability_weights = {
        "Critical": 30,
        "Injured": 30,
        "Seniors": 20,
        "Children": 20,
        "Standard": 5
    }
    score += vulnerability_weights.get(vulnerability, 5)

    # Scale by number of people affected (capped impact)
    score += min(people_count * 2, 20)

    # Generate Explainable AI Reasoning
    explanation = f"Prioritized with score {score}/100. Key factors: {emergency_type} urgency + {vulnerability} vulnerability profile for {people_count} individual(s)."

    return score, explanation