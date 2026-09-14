"""The show page's look: a two-ink risograph episode guide, as HTML and SVG.

Pure functions from data to markup, with no Streamlit import, so the page's
wording and numbers can be tested directly. The palette keeps the project's
one rule about colour: red means decline and blue means rise, here as the two
physical inks of a riso print. A third ink, yellow, carries no meaning and is
used only before the verdict is revealed, so the page cannot hint at it. Before
the reveal the page holds no chart at all: bars give a collapse away as surely
as a colour does.

There are two printings. Light mode is ink on pale paper, overprinting with
multiply as real ink does; dark mode is light ink on black stock, where inks
add up instead, so it overprints with screen. Markup never names a colour
directly, only a CSS variable, and the stylesheet decides which printing those
variables mean. The Streamlit widgets take the same two palettes from
.streamlit/config.toml.
"""

from html import escape
from math import floor

# Each palette clears the contrast it is used at: body ink against paper at
# 4.5:1, and the verdict inks at 3:1 against paper, both as marks and as the
# ground for the paper-coloured stamp lettering (tests/test_app.py checks).
# Light red is a shade deeper than the riso "bright red" it started from,
# which printed the decline stamp at 2.8:1.
LIGHT = {"paper": "#E9E8E2", "ink": "#23212B", "red": "#E83A4C", "blue": "#0078BF", "yellow": "#FFB511", "blend": "multiply"}
DARK = {"paper": "#18171C", "ink": "#ECE7DA", "red": "#FF7384", "blue": "#55B6F2", "yellow": "#FFC53D", "blend": "screen"}

PAPER, INK, RED, BLUE, YELLOW = (f"var(--{name})" for name in ("paper", "ink", "red", "blue", "yellow"))
BLEND = "var(--blend)"

VERDICT_INK = {"decline": RED, "flat": INK, "rise": BLUE}
VERDICT_LABEL = {"decline": "Clear decline", "flat": "About flat", "rise": "Clear rise"}
GUESS_WORDS = {"decline": "it declined", "flat": "it stayed about the same", "rise": "it got better"}

ESSAY_URL = "https://tariksahar.github.io/diminishing-returns/docs/essay.html"
REPO_URL = "https://github.com/tariksahar/diminishing-returns"

MINUS = "−"


def signed(value, digits=2):
    """+0.52 / −1.55, with a true minus sign; zero carries no sign."""
    text = f"{abs(value):.{digits}f}"
    if float(text) == 0:
        return text
    return ("+" if value > 0 else MINUS) + text


def signed_markup(value, digits=2):
    """signed() for the display face. Anybody draws + and − small and high, so
    the sign is set in the mono face, where it reads at a glance."""
    text = signed(value, digits)
    if text[0] in "+" + MINUS:
        return f'<span class="sign">{text[0]}</span>{text[1:]}'
    return text


def episode_code(season, episode):
    return f"S{season:02d}E{episode:02d}"


def compact_votes(votes):
    if votes >= 1_000_000:
        return f"{votes / 1_000_000:.1f}M"
    if votes >= 1_000:
        return f"{round(votes / 1_000)}k"
    return str(votes)


def years(page):
    if page["ongoing"]:
        return f"{page['start_year']}–"
    return f"{page['start_year']}–{int(page['end_year'])}"


def stylesheet():
    """Global CSS, rendered once at the top of the page. A <style> element
    applies to the whole document wherever it sits, so it also restyles
    Streamlit's own containers (the paper ground, the page width)."""
    def grain(rgb, alpha):
        return (
            "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'>"
            "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/>"
            f"<feColorMatrix values='0 0 0 0 {rgb[0]} 0 0 0 0 {rgb[1]} 0 0 0 0 {rgb[2]} 0 0 0 {alpha} 0'/></filter>"
            "<rect width='100%' height='100%' filter='url(%23n)'/></svg>"
        )

    def magnifier(stroke):
        return (
            "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' "
            f"stroke='{stroke.replace('#', '%23')}' stroke-width='2.6' stroke-linecap='square'>"
            "<circle cx='10' cy='10' r='6.5'/><path d='M15 15l6 6'/></svg>"
        )

    def tokens(palette, texture, scheme):
        declarations = " ".join(f"--{k}: {v};" for k, v in palette.items())
        return (
            f"color-scheme: {scheme}; {declarations} "
            f'--grain: url("{texture}"); --magnifier: url("{magnifier(palette["ink"])}");'
        )

    light = tokens(LIGHT, grain((0.14, 0.13, 0.17), 0.06), "light")
    dark = tokens(DARK, grain((0.93, 0.91, 0.85), 0.05), "dark")
    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Anybody:wdth,wght@50..150,100..900&family=Azeret+Mono:wght@400;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;1,6..72,400&display=swap');

/* The printing follows the visitor's system setting, as Streamlit's widgets
   do. Declaring color-scheme also tells a phone browser's forced dark mode
   that the page already has one, so it leaves the colours alone instead of
   inverting them. */
:root {{ {light} }}
@media (prefers-color-scheme: dark) {{
  :root {{ {dark} }}
}}

[data-testid="stAppViewContainer"] {{ background: var(--paper) var(--grain); }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stMainBlockContainer"] {{ max-width: 1040px; padding-top: 2.25rem; padding-bottom: 4rem; }}

/* The show search: a thick ink frame with a magnifier, so it reads as the way
   into the page rather than as a settings dropdown. Streamlit gives the
   bordered box no test id of its own, so it is reached by structure -- the
   box is the second level under stSelectbox in Streamlit 1.63, which
   app/requirements.txt pins. Focus prints a second, yellow impression offset
   like the title's. */
[data-testid="stSelectbox"] > div > div {{
  border: 3px solid var(--ink) !important; border-radius: 0 !important;
  background: var(--paper) var(--magnifier) no-repeat 14px center / 22px 22px !important;
  padding-left: 42px; min-height: 54px; transition: box-shadow .12s ease;
}}
[data-testid="stSelectbox"] > div > div:focus-within {{ box-shadow: 5px 4px 0 var(--yellow); }}
[data-testid="stSelectbox"] input {{ font-size: 19px; }}
[data-testid="stSelectbox"] button svg {{ color: var(--ink); }}
@media (prefers-reduced-motion: reduce) {{
  [data-testid="stSelectbox"] > div > div {{ transition: none; }}
}}

.riso {{ color: var(--ink); font-family: "Newsreader", Georgia, serif; }}
.riso-mono {{ font-family: "Azeret Mono", ui-monospace, monospace; font-size: 11.5px; letter-spacing: .08em; text-transform: uppercase; }}

.riso-strip {{ display: flex; justify-content: space-between; flex-wrap: wrap; gap: 6px 16px; border-bottom: 2px solid var(--ink); padding-bottom: 10px; }}
.riso-strip a {{ color: inherit; text-decoration: none; border-bottom: 1px solid currentColor; }}

.riso-title {{ position: relative; margin: 18px 0 26px; font-family: "Anybody", Impact, sans-serif; font-weight: 900; font-stretch: 150%;
  text-transform: uppercase; font-size: clamp(38px, 7vw, 84px); line-height: .86; letter-spacing: -.01em; text-wrap: balance; color: var(--ink); }}
/* The title is a div with role="heading", not an <h1>: Streamlit rebuilds
   any <h1> inside markdown as its own heading component, with its own padding
   and wrapper, which pulls the second impression out of register. */
.riso-title .plate {{ position: relative; display: block; }}
.riso-title .ghost {{ position: absolute; inset: 0; transform: translate(4px, 3px); mix-blend-mode: var(--blend); pointer-events: none; }}
.riso-strip .id {{ text-transform: none; }}

.riso-verdict {{ display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 20px 44px; align-items: start; margin-top: 4px; }}
.riso-stamp {{ display: inline-block; font-family: "Anybody", Impact, sans-serif; font-weight: 800; font-stretch: 125%; text-transform: uppercase;
  font-size: clamp(22px, 2.8vw, 30px); color: var(--paper); padding: 7px 16px 5px; }}
.riso-answer {{ font-style: italic; font-size: 18px; margin: 14px 0 0; }}
.riso-lede {{ font-size: clamp(19px, 2.1vw, 24px); line-height: 1.34; margin: 14px 0 0; max-width: 34ch; }}

.riso-facts {{ display: grid; grid-template-columns: auto 1fr; gap: 10px 18px; margin: 0; }}
.riso-facts dt {{ padding-top: 7px; }}
.riso-facts dd {{ margin: 0; font-family: "Anybody", Impact, sans-serif; font-weight: 700; font-stretch: 110%; font-size: 25px;
  font-variant-numeric: tabular-nums; border-bottom: 1px dashed color-mix(in srgb, var(--ink) 40%, transparent); padding-bottom: 8px; }}

.riso-facts .sign {{ font-family: "Azeret Mono", ui-monospace, monospace; font-weight: 600; font-size: .92em; margin-right: .06em; }}

.riso-chart svg {{ display: block; width: 100%; height: auto; }}
.riso-chart svg.narrow {{ display: none; }}
.riso-caption {{ margin: 6px 0 0; }}
.riso-empty {{ border-top: 2px solid var(--ink); padding-top: 12px; margin-bottom: 48px; }}
[data-testid="stMarkdownContainer"] .riso-empty p.riso-mono {{ font-size: 11.5px; margin: 0; }}
[data-testid="stMarkdownContainer"] p.riso-waiting {{ font-size: 11.5px; margin: 2px 0 40px; }}

.riso-context {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px 32px; border-top: 2px solid var(--ink); padding-top: 16px; }}
.riso-context p {{ margin: 6px 0 0; font-size: 17px; line-height: 1.45; max-width: 44ch; }}

.riso-foot {{ border-top: 1px dashed color-mix(in srgb, var(--ink) 40%, transparent); padding-top: 12px; display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px 20px; }}
.riso-foot a {{ color: inherit; }}

@media (max-width: 720px) {{
  .riso-verdict {{ grid-template-columns: 1fr; }}
  .riso-facts dd {{ font-size: 20px; }}
}}
@media (max-width: 560px) {{
  .riso-chart svg.wide {{ display: none; }}
  .riso-chart svg.narrow {{ display: block; }}
  .riso-facts {{ grid-template-columns: 1fr; gap: 2px; }}
  .riso-facts dd {{ margin-bottom: 10px; }}
}}
</style>"""


def masthead(page, revealed):
    """The strip and the title. Before the reveal the misregistered second
    impression is yellow; after it, it takes the verdict's ink."""
    title = escape(page["title"])
    ghost = VERDICT_INK[page["verdict"]] if revealed and page["verdict"] != "flat" else YELLOW
    imdb = f"https://www.imdb.com/title/{escape(page['show_tconst'])}/"
    return f"""<div class="riso">
  <div class="riso-strip riso-mono">
    <span>Episode guide · <a class="id" href="{imdb}" target="_blank" rel="noopener">{escape(page['show_tconst'])}</a></span>
    <span>{years(page)} · {page['n_episodes']} episodes · {page['n_seasons']} seasons · {compact_votes(page['total_votes'])} votes</span>
  </div>
  <div class="riso-title" role="heading" aria-level="1"><span class="plate">{title}<span class="ghost" aria-hidden="true" style="color:{ghost}">{title}</span></span></div>
</div>"""


# Two drawings of the same chart. An SVG scales as a whole, so the wide one
# shrunk onto a phone takes its 12-unit labels down to about 4 px. The narrow
# frame is drawn for ~350 px and swapped in by CSS below 560 px.
WIDE = {"W": 960, "H": 300, "L": 44, "R": 16, "T": 22, "B": 34, "font": 12, "label_gap": 48, "line": 6, "halo": 12}
NARROW = {"W": 520, "H": 340, "L": 34, "R": 8, "T": 18, "B": 36, "font": 15, "label_gap": 62, "line": 5, "halo": 10}


def _chart_svg(page, episodes, frame, css_class):
    W, H, L, R, T, B = (frame[k] for k in ("W", "H", "L", "R", "T", "B"))
    font = frame["font"]
    n = len(episodes)
    ratings = [e["average_rating"] for e in episodes]
    lo, hi = floor(min(ratings)), 10
    accent = VERDICT_INK[page["verdict"]]
    last_season = max(e["season_number"] for e in episodes)

    def x(i):
        return L + (W - L - R) * i / (n - 1)

    def y(r):
        return T + (H - T - B) * (hi - r) / (hi - lo)

    text = f'font-family="Azeret Mono, monospace" font-size="{font}" style="fill:{INK}"'
    parts = []
    first_final = next(i for i, e in enumerate(episodes) if e["season_number"] == last_season)
    if not page["ongoing"]:
        bx = (x(first_final - 1) + x(first_final)) / 2
        parts.append(f'<rect x="{bx:.1f}" y="{T}" width="{W - R - bx:.1f}" height="{H - T - B}" style="fill:{accent}" opacity=".14"/>')

    for tick in range(lo, hi + 1):
        parts.append(f'<line x1="{L}" x2="{W - R}" y1="{y(tick):.1f}" y2="{y(tick):.1f}" style="stroke:{INK}" stroke-opacity=".14"/>')
        parts.append(f'<text x="{L - 8}" y="{y(tick) + font / 3:.1f}" text-anchor="end" {text}>{tick}</text>')

    # Season boundaries and labels. Seasons can be a few episodes wide, so a
    # label is only printed where it clears the previous one; the last season
    # is always named, displacing its neighbour if the two would collide.
    seasons = []
    start = 0
    for i in range(1, n + 1):
        if i == n or episodes[i]["season_number"] != episodes[i - 1]["season_number"]:
            seasons.append((episodes[i - 1]["season_number"], start, i - 1))
            start = i
    labels = []
    for k, (season, a, b) in enumerate(seasons):
        cx = (x(a) + x(b)) / 2
        if not labels or cx - labels[-1][1] >= frame["label_gap"]:
            labels.append((season, cx))
        elif k == len(seasons) - 1:
            labels[-1] = (season, cx)
    for season, cx in labels:
        parts.append(f'<text x="{cx:.1f}" y="{H - 12}" text-anchor="middle" {text}>S{season:02d}</text>')
    for season, a, b in seasons:
        if b < n - 1:
            sx = (x(b) + x(b + 1)) / 2
            parts.append(f'<line x1="{sx:.1f}" x2="{sx:.1f}" y1="{T}" y2="{H - B}" style="stroke:{INK}" stroke-opacity=".3" stroke-dasharray="3 4"/>')

    bar = max(0.6, (W - L - R) / n * 0.62)
    for i, e in enumerate(episodes):
        fill = accent if not page["ongoing"] and e["season_number"] == last_season and page["verdict"] != "flat" else INK
        top = y(e["average_rating"])
        parts.append(f'<rect x="{x(i) - bar / 2:.2f}" y="{top:.1f}" width="{bar:.2f}" height="{y(lo) - top:.1f}" style="fill:{fill};mix-blend-mode:{BLEND}"/>')

    y0, y1 = page["intercept"], page["intercept"] + page["slope"]
    dash = ' stroke-dasharray="14 8"' if page["verdict"] == "flat" else ""
    line_ink = accent if page["verdict"] != "flat" else INK
    ends = f'x1="{x(0):.1f}" y1="{y(y0):.1f}" x2="{x(n - 1):.1f}" y2="{y(y1):.1f}"'
    # A band of bare paper under the line first. Without it the ink line,
    # overprinted on ink bars, disappears into them wherever it crosses.
    parts.append(f'<line {ends} style="stroke:{PAPER}" stroke-width="{frame["halo"]}" stroke-linecap="round"/>')
    parts.append(f'<line {ends} style="stroke:{line_ink};mix-blend-mode:{BLEND}" stroke-width="{frame["line"]}" stroke-linecap="round"{dash}/>')

    label = escape(page["title"])
    return (f'<svg class="{css_class}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="{label}: IMDb rating of each episode in broadcast order">{"".join(parts)}</svg>')


def chart(page, episodes):
    """Every episode as a bar of ink, in broadcast order, with the weighted
    trend line and the final season printed in the verdict's ink. Drawn only
    once the verdict is revealed."""
    return f"""<figure class="riso riso-chart" style="margin:0">
  {_chart_svg(page, episodes, WIDE, "wide")}
  {_chart_svg(page, episodes, NARROW, "narrow")}
  <figcaption class="riso-caption riso-mono">Every rated episode, in order. The line is the vote-weighted trend.</figcaption>
</figure>"""


def waiting_note():
    return """<p class="riso riso-mono riso-waiting">The chart and the verdict appear once you answer.</p>"""


def final_season_sentence(page):
    if page["ongoing"]:
        return "It is still running, so there is no final season to judge yet."
    return (
        f"Season {page['n_seasons']} averaged {page['final_season_mean']:.2f}, "
        f"after {page['rest_mean']:.2f} for everything before it."
    )


def placement_sentence(page, context):
    n = f"{context['n_shows']:,}"
    if page["verdict"] == "decline":
        return f"That is a steeper decline than {round(100 * page['share_declining_less'])}% of the {n} shows measured."
    if page["verdict"] == "rise":
        return f"That is a steeper rise than {round(100 * page['share_rising_less'])}% of the {n} shows measured."
    return f"Like {round(100 * context['share_flat'])}% of the {n} shows measured, it stays within half a point of where it started."


def answer_sentence(page, guess):
    if guess is None:
        return "You skipped the guess."
    if guess == page["verdict"]:
        return f"You called it: {GUESS_WORDS[page['verdict']]}."
    return f"Not this one. You said {GUESS_WORDS[guess]}; the ratings say {GUESS_WORDS[page['verdict']]}."


def verdict(page, episodes, context, guess):
    ink = VERDICT_INK[page["verdict"]]
    last = episodes[-1]
    if page["ongoing"]:
        final_fact = "Still running"
    elif page["final_season_sign"] == 0:
        final_fact = "Level with the rest"
    else:
        final_fact = f"{signed_markup(page['final_season_mean'] - page['rest_mean'])} vs the rest"
    return f"""<div class="riso riso-verdict">
  <div>
    <span class="riso-stamp" style="background:{ink}">{VERDICT_LABEL[page['verdict']]}</span>
    <p class="riso-answer">{escape(answer_sentence(page, guess))}</p>
    <p class="riso-lede">{escape(final_season_sentence(page))} {escape(placement_sentence(page, context))}</p>
  </div>
  <dl class="riso-facts">
    <dt class="riso-mono">Trend across the run</dt><dd>{signed_markup(page['slope'])} points</dd>
    <dt class="riso-mono">Final season</dt><dd>{final_fact}</dd>
    <dt class="riso-mono">Last episode</dt><dd>{episode_code(last['season_number'], last['episode_number'])} · {last['average_rating']:.1f}</dd>
    <dt class="riso-mono">Rated episodes</dt><dd>{page['n_episodes']}</dd>
  </dl>
</div>"""


def finale_sentence(page):
    counted, won = page["finales_counted"], page["finales_won"]
    if counted == 0:
        return "None of its seasons ran four episodes or more, so its finales are not compared."
    text = f"{won} of its {counted} season finales rated above the rest of their season."
    if not page["ongoing"] and page["series_finale_rose"] is not None:
        text += " Its last episode " + ("beat" if page["series_finale_rose"] else "did not beat") + " its final season."
    return text


def context_block(page, context):
    tier_share = round(100 * context["tier_share_declining"])
    return f"""<div class="riso riso-context">
  <div>
    <span class="riso-mono">Finales</span>
    <p>{escape(finale_sentence(page))}</p>
  </div>
  <div>
    <span class="riso-mono">Shows with a similar audience</span>
    <p>Of the {context['n_in_tier']:,} shows with {escape(context['tier_label'])}, {tier_share}% clearly decline. The better known a show, the more likely it is to be one of them, which is why the belief feels true.</p>
  </div>
</div>"""


def footer():
    return f"""<div class="riso riso-foot riso-mono">
  <span>Ratings: IMDb public datasets, snapshot of 22 July 2026. Personal and non-commercial use.</span>
  <span><a href="{ESSAY_URL}" target="_blank" rel="noopener">Read the essay</a> · <a href="{REPO_URL}" target="_blank" rel="noopener">Code and method</a></span>
</div>"""


def empty_state(n_shows):
    """What the page shows when the search has been cleared."""
    return f"""<div class="riso riso-empty">
  <p class="riso-mono">Episode guide · blank</p>
  <p class="riso-lede">Type a title above. All {n_shows:,} shows are in here, from the ones everyone remembers to the ones nobody does.</p>
</div>"""
