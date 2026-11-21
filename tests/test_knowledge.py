from assistant.service import process_request


def test_save_list_search_link_delete(session, today):
    saved = process_request("save note: Derivatives - the derivative of x^2 is 2x #calculus", session, today=today)
    assert saved["intent"] == "knowledge" and saved["notes"][0]["tags"] == ["calculus"]
    process_request("save link https://example.edu/limits Limits explained #calculus", session, today=today)

    listed = process_request("show my notes", session, today=today)
    assert "#1 Derivatives" in listed["message"] and "https://example.edu/limits" in listed["message"]

    found = process_request("find notes about derivative x^2", session, today=today)
    assert [n["id"] for n in found["notes"]] == [1]
    assert found["citations"] == [{"note_id": 1, "title": "Derivatives", "source_url": None}]
    assert [n["id"] for n in process_request("find #calculus", session, today=today)["notes"]] == [1, 2]

    process_request("essay due Friday", session, today=today)
    linked = process_request("link note 1 to essay", session, today=today)
    assert linked["message"] == 'Linked note #1 to "Essay".' and session.links == {(1, 1)}

    assert process_request("delete note 1", session, today=today)["message"] == "Deleted note #1."
    assert session.links == set() and [n.id for n in session.notes] == [2]


def test_search_ignores_vietnamese_accents(session, today):
    process_request("lưu ghi chú: Giải tích - đạo hàm và tích phân", session, today=today)
    found = process_request("tìm ghi chú về giai tich", session, today=today)
    assert found["lang"] == "vi" and found["notes"][0]["title"] == "Giải tích"


def test_no_source_is_invented(session, today):
    process_request("save note: Derivatives - the derivative of x^2 is 2x", session, today=today)
    missing = process_request("find notes about quantum physics", session, today=today)
    assert missing["notes"] == [] and missing["citations"] == [] and "no source" in missing["message"]


def test_link_needs_an_address(session, today):
    response = process_request("save link my favourite page", session, today=today)
    assert session.notes == [] and "http" in response["message"]


def test_notes_survive_a_plan_reset(session, today):
    process_request("save note: Derivatives - the derivative of x^2 is 2x", session, today=today)
    process_request("essay due Friday", session, today=today)
    process_request("reset", session, today=today)
    assert session.tasks == [] and len(session.notes) == 1


def test_find_without_notes_word_is_not_a_note_search(session, today):
    process_request("save note: Derivatives - the derivative of x^2 is 2x", session, today=today)
    assert process_request("find the library", session, today=today)["intent"] == "office"
