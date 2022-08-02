import pytest
from main import app


def test_flask_simple():
    app.config['TESTING'] = True
    client = app.test_client()
    result = client.get('/test')
    assert b'root' == result.data
