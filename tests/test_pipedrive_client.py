from unittest.mock import MagicMock, patch

import pytest

from dataenrich.crm.pipedrive_client import PipedriveClient, PipedriveError


@pytest.fixture
def client():
    return PipedriveClient(api_token="TOK123", domain="mycompany")


def test_find_organization_by_website_returns_match(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.return_value = MagicMock(
            ok=True,
            json=lambda: {"success": True, "data": {"items": [{"item": {"id": 42, "name": "Acme Co"}}]}},
        )
        org = client.find_organization_by_website("acme.example")

    assert org is not None
    assert org.id == "42"
    assert org.website == "acme.example"
    call = mock_req.call_args
    assert call.args[0] == "GET"
    assert call.args[1] == "https://mycompany.pipedrive.com/api/v1/organizations/search"
    assert call.kwargs["params"]["term"] == "acme.example"
    assert call.kwargs["params"]["api_token"] == "TOK123"


def test_find_organization_by_website_returns_none_when_not_found(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.return_value = MagicMock(ok=True, json=lambda: {"success": True, "data": {"items": []}})
        org = client.find_organization_by_website("nomatch.example")

    assert org is None


def test_create_organization_request_shape(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.return_value = MagicMock(ok=True, json=lambda: {"success": True, "data": {"id": 99}})
        org = client.create_organization("New Org", "neworg.example")

    assert org.id == "99"
    call = mock_req.call_args
    assert call.args[0] == "POST"
    assert call.kwargs["json"] == {"name": "New Org"}


def test_find_contact_by_email_returns_match(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.return_value = MagicMock(
            ok=True,
            json=lambda: {"success": True, "data": {"items": [{"item": {"id": 7, "name": "Jamie Okoye"}}]}},
        )
        contact = client.find_contact_by_email("jamie@acme.example")

    assert contact is not None
    assert contact.id == "7"
    call = mock_req.call_args
    assert call.kwargs["params"]["term"] == "jamie@acme.example"


def test_create_contact_request_shape(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.return_value = MagicMock(ok=True, json=lambda: {"success": True, "data": {"id": 5}})
        contact = client.create_contact("Jamie Okoye", "jamie@acme.example", "42")

    assert contact.id == "5"
    call = mock_req.call_args
    assert call.kwargs["json"] == {"name": "Jamie Okoye", "email": ["jamie@acme.example"], "org_id": 42}


def test_create_lead_creates_deal_and_note(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.side_effect = [
            MagicMock(ok=True, json=lambda: {"success": True, "data": {"id": 12}}),
            MagicMock(ok=True, json=lambda: {"success": True, "data": {}}),
        ]
        lead_id = client.create_lead("42", "5", "Phase 1", "some note")

    assert lead_id == "12"
    assert mock_req.call_count == 2
    deal_call, note_call = mock_req.call_args_list
    assert deal_call.args[1] == "https://mycompany.pipedrive.com/api/v1/deals"
    assert deal_call.kwargs["json"] == {"title": "Phase 1", "org_id": 42, "person_id": 5}
    assert note_call.args[1] == "https://mycompany.pipedrive.com/api/v1/notes"
    assert note_call.kwargs["json"] == {"deal_id": 12, "content": "some note"}


def test_non_ok_response_raises_pipedrive_error(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.return_value = MagicMock(ok=False, status_code=401, text="Unauthorized")
        with pytest.raises(PipedriveError, match="401"):
            client.create_organization("X", "x.example")


def test_success_false_raises_pipedrive_error(client):
    with patch("requests.Session.request") as mock_req:
        mock_req.return_value = MagicMock(ok=True, json=lambda: {"success": False, "error": "bad request"})
        with pytest.raises(PipedriveError, match="success=false"):
            client.create_organization("X", "x.example")
