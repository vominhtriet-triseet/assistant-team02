from assistant.offices import answer, find_offices, load_offices

OFFICES = load_offices()


def test_exact_name():
    assert answer("where is the library?", OFFICES) == "Library: room B.201, open Mon-Sat 07:00-20:00."


def test_longest_exact_name_wins():
    matches = find_offices("Library Circulation Service - Thu Duc Campus hours", OFFICES)
    assert [o["name"] for o in matches] == ["Library Circulation Service - Thu Duc Campus"]


def test_partial_name():
    assert answer("when does the training open", OFFICES).startswith("Training Office: room I.101")


def test_partial_name_narrowed_by_campus():
    assert "C108" in answer("library circulation thu duc", OFFICES)


def test_ambiguous_partial_name_asks_which():
    reply = answer("faculty hours", OFFICES)
    assert reply.startswith("Several offices match")
    assert "Nguyen Van Cu Campus" in reply and "Thu Duc Campus" in reply


def test_unpublished_details():
    assert "not published" in answer("where is the office of academic affairs", OFFICES)


def test_unknown_office():
    assert answer("where is the swimming pool", OFFICES) is None


def test_pronoun_it_does_not_match_it_helpdesk():
    assert answer("when does it open", OFFICES) is None
