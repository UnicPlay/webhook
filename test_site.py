import os.path
import shutil
import time
from fastapi.testclient import TestClient
from fastapi import status
from fastapi.staticfiles import StaticFiles
import pytest
import webhook
from concurrent.futures import ThreadPoolExecutor


def message(client):
    message_resp = client.post("/webhook/message/_build", headers={"state": "starting"})
    return message_resp


def upload(client):
    with open("/home/study5/dev/site/Fake site contents/_build/_build.tar", "rb") as file:
        load_resp = client.post("/webhook/download/_build",
                                headers={"Download": "true"},
                                files={"file": file})
    return load_resp


@pytest.fixture()
def client(monkeypatch, tmp_path):

    shutil.copytree('/home/study5/dev/site/static', tmp_path / 'site/static')
    shutil.copytree('/home/study5/dev/load/apps', tmp_path / 'load/apps')
    try:
        shutil.copytree('/home/study5/dev/load/_build', tmp_path / 'load/_build')
    except FileNotFoundError:
        pass
    webhook.app.mount("/static", StaticFiles(directory=str(tmp_path / 'site/static')), name="static")
    monkeypatch.setattr('webhook.HOME_PATH', tmp_path)
    print(tmp_path)
    with TestClient(webhook.app) as client:
        yield client


def test_post_successful(client):
    print(os.getcwd())
    response = message(client)
    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {"_build": "Success"}


def test_load_file_creation(client):
    message(client)
    assert os.path.exists(webhook.HOME_PATH.joinpath("load._build"))


def test_post_with_wrong_header(client):
    response = client.post("/webhook/message/_build", headers={"wrong": "header"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'error': 'Invalid request'}


def test_post_with_missing_field(client):
    response = client.post("/webhook/message/_build", json={"optional_field": "value"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'error': 'Invalid request'}


def test_index_existence(client):
    response = client.get("/")
    assert response.status_code == 200


def test_full_build_successful(client):
    message_resp = message(client)
    load_resp = upload(client)
    assert message_resp.status_code == status.HTTP_202_ACCEPTED
    assert message_resp.json() == {"_build": "Success"}
    assert load_resp.status_code == status.HTTP_200_OK
    assert os.path.isdir(load_resp.json()["path"])
    assert not os.path.exists(webhook.HOME_PATH.joinpath("error._build"))
    assert not os.path.exists(webhook.HOME_PATH.joinpath("load._build"))


def test_post_bad_download(client):
    message(client)
    response = client.post("/webhook/download/_build", headers={"qq": "gg"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["error"] == "Invalid request"


def test_fail_with_timeout(client):
    response = message(client)
    assert response.status_code == status.HTTP_202_ACCEPTED
    time.sleep(2)
    assert os.path.exists(webhook.HOME_PATH.joinpath("error._build"))
    load_resp = upload(client)
    assert load_resp.status_code == status.HTTP_408_REQUEST_TIMEOUT
    assert load_resp.json() == {"error": "_build timed out or was not requested"}


def test_crash_during_loading(client):
    response = message(client)
    assert response.status_code == status.HTTP_202_ACCEPTED
    client.close()
    assert os.path.exists(webhook.HOME_PATH.joinpath("load._build"))
    with TestClient(webhook.app):
        pass
    assert os.path.exists(webhook.HOME_PATH.joinpath("error._build"))


def test_get_non_existing_html(client):
    response = client.get("/non_existing/page.html")
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_concurrent_post_requests(client):
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(message, client) for _ in range(3)]
        for future in futures:
            response = future.result()
            assert response.status_code == status.HTTP_202_ACCEPTED


def test_open_page_while_loading(client):
    assert message(client).status_code == status.HTTP_202_ACCEPTED
    response = client.get("/_build/index.html")
    assert response.status_code == status.HTTP_307_TEMPORARY_REDIRECT


def test_open_page_with_error(client):
    assert message(client).status_code == status.HTTP_202_ACCEPTED
    time.sleep(2)
    assert client.get("/_build/index.html").status_code == status.HTTP_404_NOT_FOUND


def test_sending_bad_file(client):
    assert client.post("/webhook/message/bad", headers={"state": "bad tar"}).status_code == status.HTTP_202_ACCEPTED
    with open("/home/study5/dev/site/Fake site contents/bad.tar", "rb") as file:
        load_resp = client.post("/webhook/download/bad",
                                headers={"Download": "true"},
                                files={"file": file})
    assert load_resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert load_resp.json() == {"error": "Invalid or corrupted file"}


def test_send_file_without_message(client):
    load_resp = upload(client)
    assert load_resp.status_code == status.HTTP_408_REQUEST_TIMEOUT
    assert load_resp.json() == {"error": "_build timed out or was not requested"}


def test_empty_post(client):
    response = client.post("/webhook/message/empty")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {'error': 'Invalid request'}


def test_wrong_file_format(client):
    assert client.post("/webhook/message/wrong",
                       headers={"state": "wrong format"}).status_code == status.HTTP_202_ACCEPTED
    with open("/home/study5/dev/site/Fake site contents/wrong.txt", "rb") as file:
        load_resp = client.post("/webhook/download/wrong",
                                headers={"Download": "true"},
                                files={"file": file})
    assert load_resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert load_resp.json() == {"error": "Invalid or corrupted file"}


def test_uploading_multiple_files(client):
    assert client.post("/webhook/message/many",
                       headers={"state": "too many files"}).status_code == status.HTTP_202_ACCEPTED

    with open("/home/study5/dev/site/Fake site contents/bad.tar", "rb") as file1,\
         open("/home/study5/dev/site/Fake site contents/wrong.txt", "rb") as file2:
        load_resp = client.post(
            "/webhook/multiple_files",
            files={
                "files": [("file1.txt", file1, "text/plain"), ("file2.txt", file2, "text/plain")],
            },
        )
    assert load_resp.status_code == 405
    assert load_resp.json() == {'detail': 'Method Not Allowed'}


def test_connection_error(client):
    assert client.post("/webhook/message/big",
                       headers={"state": "connection issue"}).status_code == status.HTTP_202_ACCEPTED
    response = client.post("/webhook/download/big",
                files={"big.tar": "/home/study5/dev/site/Fake site contents/big.tar"},
                timeout=0.1)
    assert os.path.exists(webhook.HOME_PATH.joinpath("error._build"))
    assert response.status_code == status.HTTP_418_IM_A_TEAPOT
