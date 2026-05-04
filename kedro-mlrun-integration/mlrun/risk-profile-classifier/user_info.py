"""
Nuclio function for generating random user data for risk profile classification.

Takes a user name in the request body and returns random user financial data.
"""

import json
import random
import hashlib


def handler(context, event):
    """
    Nuclio handler: generate random user financial data based on user name.
    
    Request body:
        {"user_name": "John Doe"}
        
    Response:
        {
            "age": 22,
            "income": 1200,
            "investment_experience_years": 20,
            "savings_ratio": 0.35,
            "debt_ratio": 0.10,
            "risk_tolerance_score": 3,
            "portfolio_volatility": 0.10
        }
    """
    try:
        # Parse request body
        if event.body:
            if isinstance(event.body, bytes):
                data = json.loads(event.body.decode("utf-8"))
            elif isinstance(event.body, str):
                data = json.loads(event.body)
            else:
                data = event.body
        else:
            data = {}
        
        # Get user name (optional - used as seed for reproducibility)
        user_name = data.get("user_name")
        
        # Use user_name hash as seed for reproducible data, or random if no name
        if user_name:
            seed = int(hashlib.md5(user_name.encode()).hexdigest()[:8], 16)
            random.seed(seed)
        
        # Generate random user financial data
        age = random.randint(18, 80)
        
        result = {
            "age": age,
            "income": random.randint(20000, 200000),
            "investment_experience_years": random.randint(0, min(40, age - 18)),
            "savings_ratio": round(random.uniform(0.05, 0.50), 2),
            "debt_ratio": round(random.uniform(0.0, 0.60), 2),
            "risk_tolerance_score": random.randint(1, 10),
            "portfolio_volatility": round(random.uniform(0.05, 0.40), 2)
        }
        
        context.logger.info(f"Generated random user data for: {user_name or 'anonymous'}")
        
        return context.Response(
            body=json.dumps(result),
            content_type="application/json",
            status_code=200,
        )
        
    except Exception as e:
        context.logger.error(f"Error: {str(e)}")
        return context.Response(
            body=json.dumps({"error": str(e)}),
            content_type="application/json",
            status_code=500,
        )

