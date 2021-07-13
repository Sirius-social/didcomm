import json
import uuid
import asyncio
from time import sleep

from databases import Database
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_db
from app.utils import build_endpoint_url
from app.db.crud import ensure_endpoint_exists
from app.settings import WS_PATH_PREFIX

from .helpers import override_sirius_sdk, override_get_db


client = TestClient(app)
app.dependency_overrides[get_db] = override_get_db


def test_delivery_via_websocket(test_database: Database, random_me: (str, str, str), random_endpoint_uid: str):
    """Check any content posted to endpoint is delivered to Client websocket connection
    """
    # Override original database with test one
    content = b'{"protected": "eyJlbmMiOiAieGNoYWNoYTIwcG9seTEzMDVfaWV0ZiIsICJ0eXAiOiAiSldNLzEuMCIsICJhbGciOiAiQXV0aGNyeXB0IiwgInJlY2lwaWVudHMiOiBbeyJlbmNyeXB0ZWRfa2V5IjogInBKcW1xQS1IVWR6WTNWcFFTb2dySGx4WTgyRnc3Tl84YTFCSmtHU2VMT014VUlwT0RQWTZsMVVsaVVvOXFwS0giLCAiaGVhZGVyIjogeyJraWQiOiAiM1ZxZ2ZUcDZRNFZlRjhLWTdlVHVXRFZBWmFmRDJrVmNpb0R2NzZLR0xtZ0QiLCAic2VuZGVyIjogIjRlYzhBeFRHcWtxamd5NHlVdDF2a0poeWlYZlNUUHo1bTRKQjk1cGZSMG1JVW9KajAwWmswNmUyUEVDdUxJYmRDck8xeTM5LUhGTG5NdW5YQVJZWk5rZ2pyYV8wYTBQODJpbVdNcWNHc1FqaFd0QUhOcUw1OGNkUUYwYz0iLCAiaXYiOiAiVU1PM2o1ZHZwQnFMb2Rvd3V0c244WEMzTkVqSWJLb2oifX1dfQ==", "iv": "MchkHF2M-4hneeUJ", "ciphertext": "UgcdsV-0rIkP25eJuRSROOuqiTEXp4NToKjPMmqqtJs-Ih1b5t3EEbrrHxeSfPsHtlO6J4OqA1jc5uuD3aNssUyLug==", "tag": "sQD8qgJoTrRoyQKPeCSBlQ=="}'
    content_type = 'application/ssi-agent-wire'

    agent_did, agent_verkey, agent_secret = random_me
    redis_pub_sub = 'redis://redis1/%s' % uuid.uuid4().hex

    asyncio.get_event_loop().run_until_complete(ensure_endpoint_exists(
        db=test_database, uid=random_endpoint_uid, redis_pub_sub=redis_pub_sub,
        agent_id=agent_did, verkey=agent_verkey
    ))
    with client.websocket_connect(f"/{WS_PATH_PREFIX}?endpoint={random_endpoint_uid}") as websocket:
        sleep(3)  # give websocket timeout to accept connection
        response = client.post(
            build_endpoint_url(random_endpoint_uid),
            headers={"Content-Type": content_type},
            data=content,
        )
        assert response.status_code == 200

        enc_msg = websocket.receive_json()
        assert enc_msg == json.loads(content.decode())

        # Close websocket
        websocket.close()
        sleep(3)  # give websocket timeout to accept connection
        url = build_endpoint_url(random_endpoint_uid)
        response = client.post(
            url,
            headers={"Content-Type": content_type},
            data=content,
        )
        assert response.status_code == 410
