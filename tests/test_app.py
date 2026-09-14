"""The show-lookup app (app/): its markup, its queries and its page flow.

Three layers, tested separately:
  * riso.py turns a show's data into markup. Checked for every one of the
    3,234 shows, because the edge cases -- 1,211 episodes, 54 seasons, no
    season long enough to judge a finale -- are exactly the ones nobody opens
    by hand.
  * lookup.py fetches that data with SQL. Its numbers are already tied to the
    published findings by tests/test_sql_analysis.py; here it is checked for
    how it handles ids that do not exist.
  * streamlit_app.py is driven headless with Streamlit's AppTest: pick, guess,
    rerun, switch. The two subtle ones were each run against the naive code
    they guard against, and that code fails them.

Run from the repository root:  pytest
"""

import re
import sys
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))

import riso  # noqa: E402
from lookup import ShowLookup  # noqa: E402

GOT = "tt0944947"
BREAKING_BAD = "tt0903747"
FRIENDS = "tt0108778"


@pytest.fixture(scope="module")
def lookup():
    return ShowLookup()


@pytest.fixture(scope="module")
def every_show(lookup):
    shows = []
    for row in lookup.catalogue():
        page = lookup.page(row["show_tconst"])
        shows.append((page, lookup.episodes(row["show_tconst"]), lookup.context(page["audience_tier"])))
    return shows


def test_catalogue_labels_tell_every_show_apart(lookup):
    catalogue = lookup.catalogue()
    labels = [f"{r['title']} ({r['start_year']})" for r in catalogue]
    assert len(catalogue) == 3_234
    assert len(set(labels)) == len(labels)


def test_unknown_or_hostile_ids_find_nothing(lookup):
    """Ids reach SQL as bound parameters, so a value shaped like an injection
    is just a string that matches no show."""
    assert lookup.page("tt0000000") is None
    assert lookup.page("x' OR '1'='1") is None
    assert lookup.episodes("x' OR '1'='1") == []


def test_every_show_renders(every_show):
    for page, episodes, context in every_show:
        riso.masthead(page, revealed=False)
        riso.masthead(page, revealed=True)
        riso.chart(page, episodes)
        riso.verdict(page, episodes, context, guess=None)
        riso.context_block(page, context)


def test_the_masthead_gives_nothing_away_before_the_reveal(every_show):
    """No verdict ink and no verdict word in the part of the page shown before
    the guess. (The chart is not shown then at all; see
    test_before_the_guess_the_page_holds_no_chart.)"""
    for page, _, _ in every_show:
        before = riso.masthead(page, revealed=False)
        assert riso.RED not in before and riso.BLUE not in before, page["title"]
        for label in riso.VERDICT_LABEL.values():
            assert label not in before, page["title"]


def test_season_labels_never_collide(every_show):
    """In both drawings: the wide one and the one swapped in on a phone."""
    for page, episodes, _ in every_show:
        for frame in (riso.WIDE, riso.NARROW):
            svg = riso._chart_svg(page, episodes, frame, "x")
            xs = [float(v) for v in re.findall(r'<text x="([\d.]+)" y="\d+" text-anchor="middle"', svg)]
            assert xs, page["title"]
            assert all(b - a >= frame["label_gap"] for a, b in zip(xs, xs[1:])), page["title"]


def test_show_titles_are_escaped():
    """Titles go into markup that Streamlit renders as trusted HTML."""
    page = {"title": '<img src=x onerror="alert(1)">', "show_tconst": "tt1", "verdict": "decline",
            "ongoing": 0, "start_year": 2000, "end_year": 2001, "n_episodes": 13, "n_seasons": 2,
            "total_votes": 1000}
    markup = riso.masthead(page, revealed=True)
    assert "<img" not in markup
    assert "&lt;img" in markup


def test_signed_numbers_use_a_true_minus_and_no_negative_zero():
    assert riso.signed(-1.546) == "−1.55"
    assert riso.signed(0.518) == "+0.52"
    assert riso.signed(-0.001) == "0.00"


def test_the_game_of_thrones_page_says_what_the_analysis_says(lookup):
    page = lookup.page(GOT)
    context = lookup.context(page["audience_tier"])
    episodes = lookup.episodes(GOT)
    text = riso.verdict(page, episodes, context, guess="rise") + riso.context_block(page, context)
    assert "Clear decline" in text
    assert "Season 8 averaged 6.40, after 8.95" in text
    assert "steeper decline than 97% of the 3,234 shows" in text
    assert "Not this one." in text
    assert "7 of its 8 season finales" in text
    assert "Of the 60 shows with 500,000 votes or more, 43% clearly decline" in text


def test_a_tied_final_season_reads_as_level(lookup):
    tied = lookup._rows("SELECT show_tconst FROM show_pages WHERE final_season_sign = 0 LIMIT 1")[0]["show_tconst"]
    page = lookup.page(tied)
    context = lookup.context(page["audience_tier"])
    assert "Level with the rest" in riso.verdict(page, lookup.episodes(tied), context, guess=None)


# --- the running app ---------------------------------------------------------

streamlit_testing = pytest.importorskip("streamlit.testing.v1")


def start(show=None):
    app = streamlit_testing.AppTest.from_file(str(APP_DIR / "streamlit_app.py"), default_timeout=120)
    if show is not None:
        app.query_params["show"] = show
    return app.run()


def revealed(app):
    return 'class="riso-stamp"' in "".join(block.value for block in app.markdown)


def test_opens_on_game_of_thrones_with_the_verdict_hidden():
    app = start()
    assert not app.exception
    assert app.selectbox[0].value == GOT
    assert not revealed(app)


def test_before_the_guess_the_page_holds_no_chart():
    """An earlier version drew the episode bars above the guess, and bars answer
    the question on sight -- Game of Thrones' last season drops off a cliff. A
    test that only looked for verdict colours and words passed it anyway. This
    one checks the page itself: no chart until the verdict is shown."""
    def content(app):
        # The stylesheet is left out: it names chart classes and inlines an
        # SVG texture, and neither puts a chart on the page.
        return "".join(b.value for b in app.markdown if not b.value.lstrip().startswith("<style>"))

    app = start()
    before = content(app)
    assert "<svg" not in before
    assert "riso-chart" not in before
    app.segmented_control[0].set_value("flat").run()
    assert '<figure class="riso riso-chart"' in content(app)


def test_skip_sits_directly_under_the_question():
    app = start()
    kinds = [type(element).__name__ for element in app.main.children.values()]
    question = kinds.index("ButtonGroup")
    assert kinds[question + 1] == "Button"
    assert app.button[0].label == "Skip the guess"


def test_a_guess_reveals_the_verdict_and_stays_revealed():
    """The guess buttons vanish on reveal, and Streamlit forgets a widget's
    value once it is not drawn. Keeping the guess only in the widget's own key
    reveals the verdict and then closes it again on the very next rerun --
    checked, not assumed."""
    app = start()
    app.segmented_control[0].set_value("decline").run()
    assert revealed(app)
    app.run()
    app.run()
    assert revealed(app)


def test_every_pick_sticks_and_guesses_are_kept_per_show():
    """The first running version passed the URL's show as the selectbox index
    on every run; the changing index made Streamlit treat the box as a new
    widget and discard the visitor's second pick. This test is what caught it."""
    app = start()
    app.segmented_control[0].set_value("decline").run()
    for show in [BREAKING_BAD, GOT, FRIENDS, BREAKING_BAD]:
        app.selectbox[0].set_value(show).run()
        assert app.selectbox[0].value == show
        assert app.query_params["show"] == [show]
        assert revealed(app) == (show == GOT)


def test_a_shared_link_opens_its_show_and_a_bad_one_falls_back():
    assert start(FRIENDS).selectbox[0].value == FRIENDS
    bad = start("x' OR 1=1 --")
    assert not bad.exception
    assert bad.selectbox[0].value == GOT


def test_skipping_the_guess_reveals_without_an_answer():
    app = start(BREAKING_BAD)
    next(b for b in app.button if b.label == "Skip the guess").click().run()
    assert revealed(app)
    assert "You skipped the guess." in "".join(block.value for block in app.markdown)


def _contrast(a, b):
    def luminance(hex_colour):
        channels = [int(hex_colour.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
    hi, lo = sorted([luminance(a), luminance(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@pytest.mark.parametrize("name", ["LIGHT", "DARK"])
def test_both_printings_are_legible(name):
    """WCAG contrast for how each colour is actually used: running text in ink
    on paper (4.5:1), and the verdict inks as marks on paper and as the ground
    of the paper-coloured stamp lettering, which is large bold type (3:1). The
    first light palette printed 'Clear decline' at 2.8:1."""
    palette = getattr(riso, name)
    assert _contrast(palette["ink"], palette["paper"]) >= 4.5
    for ink in ("red", "blue"):
        assert _contrast(palette[ink], palette["paper"]) >= 3.0, ink


def test_markup_names_no_colour_directly(every_show):
    """Colours come from CSS variables, so the dark printing reaches every
    element. A literal hex in the markup would stay light-mode on black stock."""
    page, episodes, context = every_show[0]
    markup = (riso.masthead(page, True) + riso.chart(page, episodes)
              + riso.verdict(page, episodes, context, guess=None) + riso.context_block(page, context)
              + riso.footer()
              + riso.game_intro([{"show_tconst": "tt1", "verdict": "decline"}], {"tt1": "flat"}, {},
                                {"n_shows": 60, "n_declined": 26}))
    assert not re.search(r"#[0-9A-Fa-f]{6}\b", markup)
    assert not re.search(r'\b(fill|stroke)="#', markup)


def test_the_theme_config_carries_the_same_two_palettes():
    import tomllib
    config = tomllib.loads((APP_DIR.parent / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
    assert "base" not in config["theme"], "a base theme would pin every visitor to one printing"
    for section, palette in (("light", riso.LIGHT), ("dark", riso.DARK)):
        assert config["theme"][section]["backgroundColor"] == palette["paper"]
        assert config["theme"][section]["textColor"] == palette["ink"]


def cards(app):
    return [b for b in app.button if b.key and b.key.startswith("card-")]


def card_id(button):
    return button.key.split("-")[1]


def test_a_hand_is_six_distinct_household_names_and_a_new_one_never_repeats_it(lookup):
    hand = lookup.deal()
    ids = [c["show_tconst"] for c in hand]
    assert len(set(ids)) == 6
    assert all(lookup.page(i)["audience_tier"] == 4 for i in ids)
    again = lookup.deal(exclude=ids)
    assert len(again) == 6 and not set(ids) & {c["show_tconst"] for c in again}
    assert lookup.household_names() == {"n_shows": 60, "n_declined": 26}


def test_game_cards_never_carry_a_verdict(lookup):
    for card in lookup.deal(n=60):
        label = riso.card_label(card, guess=None, skipped=False)
        for word in list(riso.VERDICT_LABEL.values()) + ["declin", "flat", "rise"]:
            assert word.lower() not in label.lower().replace(card["title"].lower(), ""), card["title"]


def test_the_score_only_tallies_the_hand_once_every_card_is_played():
    hand = [{"show_tconst": f"tt{i}", "verdict": v} for i, v in enumerate(["decline", "flat", "rise"])]
    household = {"n_shows": 60, "n_declined": 26}
    partial = riso.game_intro(hand, {"tt0": "decline"}, {}, household)
    assert "called 1 of 1" in partial and "Of these six" not in partial
    done = riso.game_intro(hand, {"tt0": "decline", "tt1": "rise"}, {"tt2": True}, household)
    assert "You called 1 of 2" in done and "1 clearly declined" in done and "26 did" in done


def test_clearing_the_search_deals_a_hand_to_play():
    app = start()
    app.selectbox[0].set_value(None).run()
    assert not app.exception
    assert "show" not in app.query_params
    assert len(cards(app)) == 6
    content = "".join(b.value for b in app.markdown if not b.value.lstrip().startswith("<style>"))
    assert "How many of them declined?" in content


def test_a_card_opens_its_show_unrevealed_and_is_marked_once_played():
    app = start()
    app.selectbox[0].set_value(None).run()
    first = cards(app)[0]
    chosen = card_id(first)
    first.click().run()
    assert app.selectbox[0].value == chosen
    assert app.query_params["show"] == [chosen]
    assert not revealed(app)

    app.segmented_control[0].set_value("decline").run()
    app.selectbox[0].set_value(None).run()
    played = [b for b in cards(app) if card_id(b) == chosen]
    assert played and played[0].key.endswith("-played")
    assert len(cards(app)) == 6, "the hand must survive a visit to one of its shows"


def test_dealing_again_brings_six_new_shows():
    app = start()
    app.selectbox[0].set_value(None).run()
    before = {card_id(b) for b in cards(app)}
    next(b for b in app.button if b.label == "Deal six more").click().run()
    after = {card_id(b) for b in cards(app)}
    assert len(after) == 6 and before.isdisjoint(after)
