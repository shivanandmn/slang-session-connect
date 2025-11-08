import os
import json
import importlib

def setup_module(module):
    os.environ["LIVEKIT_URL"] = "https://example.livekit"
    os.environ["LIVEKIT_API_KEY"] = "key"
    os.environ["LIVEKIT_API_SECRET"] = "secret"
    importlib.invalidate_caches()

def test_config_validation():
    mod = importlib.import_module("main")
    assert mod._validate_config() is None

def test_query_params_bool_parse():
    from main import QueryParams
    assert QueryParams(new_conversation="true").new_conversation is True
    assert QueryParams(new_conversation="0").new_conversation is False

def test_connection_details_schema():
    from main import ConnectionDetails
    payload = ConnectionDetails(
        serverUrl="u", roomName="r", participantName="p", participantToken="t"
    ).model_dump()
    assert set(payload.keys()) == {"serverUrl", "roomName", "participantName", "participantToken"}