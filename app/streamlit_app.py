"""Did It Decline? -- look up any of the 3,234 shows in the analysis.

Run from the repository root:
    streamlit run app/streamlit_app.py

How Streamlit works, in one paragraph: this whole file runs from top to bottom
every time a visitor does anything -- picks a show, clicks a guess. There are
no callbacks to wire up; a widget call such as st.selectbox() simply returns
its current value on each run. Anything expensive is wrapped in a cache so it
happens once rather than on every run, and anything that must survive between
runs lives in st.session_state.
"""

import streamlit as st

import riso
from lookup import ShowLookup


def show_html(markup):
    # st.markdown rather than st.html: st.html runs its input through a
    # sanitizer that strips inline <svg> and page-level <style>, which is the
    # chart and the whole look. unsafe_allow_html means Streamlit trusts this
    # markup as written, so every piece of data in it -- show titles above all
    # -- is escaped in riso.py before it gets here.
    st.markdown(markup, unsafe_allow_html=True)


DEFAULT_SHOW = "tt0944947"  # Game of Thrones

st.set_page_config(page_title="Did It Decline?", page_icon="📺", layout="centered")


@st.cache_resource
def get_lookup():
    # cache_resource: build the database once per server process and share the
    # same object with every visitor, instead of reloading 192,720 episodes on
    # each click.
    return ShowLookup()


lookup = get_lookup()
show_html(riso.stylesheet())

catalogue = lookup.catalogue()
labels = {row["show_tconst"]: f"{row['title']} ({row['start_year']})" for row in catalogue}
ids = list(labels)

# The chosen show lives in the URL (?show=tt0944947), so a page can be shared.
#
# The URL is read once, when a visitor arrives, to seed the widget's state.
# Passing it as the selectbox's `index` on every run instead looks equivalent
# and is not: Streamlit identifies a widget partly by its arguments, so an index
# that changes after each pick makes it a "new" widget, which resets to that
# index and silently throws away the visitor's second choice.
if "show" not in st.session_state:
    requested = st.query_params.get("show", DEFAULT_SHOW)
    st.session_state["show"] = requested if requested in labels else DEFAULT_SHOW

# index=None is what gives the box its clear (x) button: Streamlit only offers
# one on a selectbox that is allowed to be empty. The value still starts on a
# show, from the session state seeded above.
show = st.selectbox(
    "Pick a show",
    ids,
    index=None,
    key="show",
    format_func=labels.get,
    placeholder="Type a title",
)

if show is None:
    # Cleared with the x. Rather than an empty page, a hand of six household
    # names to call. The hand is dealt once and kept in session state: dealt
    # inline, every click anywhere would rerun the script and reshuffle it.
    st.query_params.pop("show", None)
    if "hand" not in st.session_state:
        st.session_state["hand"] = lookup.deal()
    hand = st.session_state["hand"]

    def open_show(show_id):
        # Runs before the next rerun, which is the only moment a widget's own
        # key (the selectbox's "show") may still be written.
        st.session_state["show"] = show_id

    def deal_more():
        st.session_state["hand"] = lookup.deal(exclude=[card["show_tconst"] for card in hand])

    guesses = {c["show_tconst"]: st.session_state.get(f"guess-{c['show_tconst']}") for c in hand}
    skips = {c["show_tconst"]: st.session_state.get(f"skip-{c['show_tconst']}", False) for c in hand}
    show_html(riso.game_intro(hand, guesses, skips, lookup.household_names()))

    columns = st.columns(3)
    for i, card in enumerate(hand):
        show_id = card["show_tconst"]
        played = guesses[show_id] is not None or skips[show_id]
        with columns[i % 3]:
            st.button(
                riso.card_label(card, guesses[show_id], skips[show_id]),
                key=f"card-{show_id}-{'played' if played else 'open'}",
                on_click=open_show,
                args=(show_id,),
                width="stretch",
            )
    st.button("Deal six more", type="tertiary", on_click=deal_more)

    show_html(riso.footer())
    st.stop()

st.query_params["show"] = show

page = lookup.page(show)
episodes = lookup.episodes(show)
context = lookup.context(page["audience_tier"])

# A guess is remembered per show, so switching shows starts a fresh guess.
#
# The guess buttons disappear once the verdict shows, and Streamlit forgets the
# value of any widget that is not drawn on a run. So the guess is copied, the
# moment it is made, into a key of its own that no widget owns and nothing
# clears -- otherwise the page would close itself again on the next click.
widget_key = f"guess-widget-{show}"
guess_key = f"guess-{show}"
skip_key = f"skip-{show}"


def keep_guess():
    st.session_state[guess_key] = st.session_state[widget_key]


guess = st.session_state.get(guess_key)
revealed = guess is not None or st.session_state.get(skip_key, False)

show_html(riso.masthead(page, revealed))

# Before the reveal the page shows the question and nothing that answers it.
# That includes the chart: bars alone give a collapse away at a glance, so it
# appears only with the verdict.
if not revealed:
    st.segmented_control(
        "Before you look: did it get worse?",
        ["decline", "flat", "rise"],
        format_func={"decline": "It declined", "flat": "It stayed about the same", "rise": "It got better"}.get,
        key=widget_key,
        on_change=keep_guess,
    )
    if st.button("Skip the guess", type="tertiary"):
        st.session_state[skip_key] = True
        st.rerun()
    show_html(riso.waiting_note())
else:
    show_html(riso.verdict(page, episodes, context, guess))
    show_html(riso.chart(page, episodes))
    show_html(riso.context_block(page, context))

show_html(riso.footer())
