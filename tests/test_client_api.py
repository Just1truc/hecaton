import pytest
from unittest.mock import MagicMock, patch
from hecaton.client.managers.api import HecatonServer

def test_api_login_success():
    # Patch where it is defined/imported in the target module
    with patch('hecaton.client.managers.api.requests.post') as mock_post:
        mock_post.return_value.ok = True
        mock_post.return_value.json.return_value = {"access_token": "token123"}
        
        res = HecatonServer.login("localhost:8000", "admin", "pass")
        assert res == {"access_token": "token123"}

def test_api_login_fail():
    with patch('hecaton.client.managers.api.requests.post') as mock_post:
        mock_post.return_value.ok = False
        
        res = HecatonServer.login("localhost:8000", "admin", "wrong")
        assert res is None

def test_list_workers_success():
    # Patch call_endpoint since list_workers uses it
    with patch('hecaton.client.managers.api.HecatonServer.call_endpoint') as mock_call:
        mock_call.return_value.ok = True
        mock_call.return_value.json.return_value = [[1, "IDLE", "2023-01-01"]]
        
        res = HecatonServer.list_workers("localhost:8000", "token")
        assert len(res) == 1
        assert res[0][1] == "IDLE"

def test_create_user_success():
    with patch('hecaton.client.managers.api.HecatonServer.call_endpoint') as mock_call:
        mock_call.return_value.ok = True
        mock_call.return_value.json.return_value = {"message": "User created"}
        
        res = HecatonServer.create_user("localhost", "token", "newuser", "pass", "user")
        assert res == "User created"
