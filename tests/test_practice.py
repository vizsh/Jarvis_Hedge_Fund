from backend import practice as p


def test_classifier_on_the_suggested_replies():
    for sc in p.SCENARIOS.values():
        for n in sc["nodes"]:
            kinds = [p.classify(h) for h in n["hints"]]
            assert kinds[0] == "comply", (n["hints"][0], kinds)
            assert kinds[2] == "refuse", (n["hints"][2], kinds)
            assert kinds[1] in ("verify", "stall"), (n["hints"][1], kinds)


def test_giving_a_code_loses_and_refusing_wins():
    assert p.scam_step("kyc", 1, "It is 482913.")["status"] == "lost"
    assert p.scam_step("kyc", 1, "No, banks never ask for codes")["status"] == "won"
    assert p.scam_step("kyc", 0, "Okay, what do I need to do?")["status"] == "continue"


def test_overlap_is_symmetric_and_sector_funds_do_not_overlap():
    n = lambda t: t
    a = p.overlap("largecap_a", "bluechip_b", n)
    b = p.overlap("bluechip_b", "largecap_a", n)
    assert a["overlap_pct"] == b["overlap_pct"] and a["verdict"] == "red"
    assert p.overlap("it_fund", "pharma_fund", n)["overlap_pct"] == 0


def test_hindi_replies_survive_transcriber_misspellings():
    from backend.practice_hi import classify_hi
    # what Whisper actually returned for synthesized speech of the refusals
    assert classify_hi("नहीं मैं कोई, अप डाउनलोड नहीं करुंगा नमसते.") == "refuse"
    assert classify_hi("यह तगी है, मैं फों कात रहा हूं") == "refuse"
    assert classify_hi("कोर है चार 82913") == "comply"
    assert classify_hi("कोड है चार आठ दो नौ एक तीन") == "comply"
    assert classify_hi("तीक है, मुझे क्या करना होगा?") == "comply"


def test_codes_spoken_as_number_words_count_as_giving_the_code():
    assert p.classify("it is four eight two nine one three") == "comply"
    assert p.scam_step("kyc", 1, "four eight two nine one three")["status"] == "lost"
