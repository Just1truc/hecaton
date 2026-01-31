from datetime import timedelta
from hecaton.server.auth import create_access_token, verify_password, get_password_hash, decode_access_token, ALGORITHM
from jose import jwt
import pytest
import pytest

SECRET_KEY = "test_secret_key"

def test_password_hashing():
    password = "secret_password"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)

def test_token_creation_and_decoding():
    data = {"sub": "testuser", "role": "user"}
    token = create_access_token(data, SECRET_KEY, expires_delta=timedelta(minutes=15))
    
    decoded_data = decode_access_token(token, SECRET_KEY)
    assert decoded_data is not None
    assert decoded_data.username == "testuser"
    assert decoded_data.role == "user"

def test_token_expiration():
    data = {"sub": "testuser", "role": "user"}
    # Create a token that expired 1 minute ago
    token = create_access_token(data, SECRET_KEY, expires_delta=timedelta(minutes=-1))
    
    # decode_access_token should catch the ExpiredSignatureError and return None or raise
    # looking at auth.py specific implementation, it catches JWTError and returns None
    decoded = decode_access_token(token, SECRET_KEY)
    assert decoded is None

def test_invalid_token():
    token = "invalid.token.string"
    decoded = decode_access_token(token, SECRET_KEY)
    assert decoded is None
