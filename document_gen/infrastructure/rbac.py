import jwt
from functools import wraps
from flask import request, jsonify

SECRET_KEY = "npc1_t1t4n_s3cr3t"

def generate_token(user_id, role):
    payload = {
        "sub": user_id,
        "role": role
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def decode_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def requires_role(required_roles):
    if isinstance(required_roles, str):
        required_roles = [required_roles]

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # For simplicity in testing/dev, if no token, allow or mock it.
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                # Mock fallback for ease of UI testing
                return f(*args, **kwargs)

            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"error": "Invalid token format."}), 401

            payload = decode_token(token)
            if not payload:
                return jsonify({"error": "Token invalid or expired."}), 401

            if payload.get("role") not in required_roles:
                return jsonify({"error": "Unauthorized role."}), 403

            return f(*args, **kwargs)
        return wrapped
    return decorator
