import pytest


@pytest.mark.e2e
async def test_root_redirects_to_swagger(api_client):
    response = await api_client.get("/")

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"
