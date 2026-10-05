"""Starting baskets: every persona only names real features, the pitch basket has everything, and free audiences pay nothing."""
from backend import setup


def test_every_basket_names_only_real_features():
    for p in setup.PERSONAS:
        assert set(p["features"]) <= set(setup.ALL_IDS), p["id"]


def test_the_pitch_basket_has_every_feature_and_the_rural_baskets_are_free():
    pitch = next(p for p in setup.PERSONAS if p["id"] == "pitch")
    assert set(pitch["features"]) == set(setup.ALL_IDS)
    for pid in ("farmers", "shg"):
        p = next(x for x in setup.PERSONAS if x["id"] == pid)
        assert p["price"] == 0 and all(f["tier"] == "free" for f in setup.FEATURES if f["id"] in p["features"])


def test_five_baskets_and_every_feature_belongs_to_some_basket():
    assert len(setup.PERSONAS) == 5
    covered = {f for p in setup.PERSONAS for f in p["features"]}
    assert covered == set(setup.ALL_IDS)


def test_saving_and_reading_a_setup_round_trips(tmp_path):
    import sqlite3
    conn = sqlite3.connect(tmp_path / "s.db")
    conn.row_factory = sqlite3.Row
    assert setup.current(conn)["done"] is False
    cur = setup.save(conn, "banks", ["rural", "govern", "bogus"])
    assert cur["done"] and cur["persona"] == "banks" and cur["features"] == ["home", "rural", "govern"]
    assert setup.price_of(cur["features"]) == 499
