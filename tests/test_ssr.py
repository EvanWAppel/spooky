"""Server-rendered, crawlable content pages (Group R.3, TASKS R-09).

TDD: written before ``components/ssr.py`` exists. These pages are what a crawler
or a no-JS visitor sees — plain semantic HTML rendered from the JSON, with the
episode text *in the raw markup* (the whole point: PRD §4.1). Same legal posture
as the app — no imagery, no synopses, no IMDb numbers (C1–C3).
"""

from __future__ import annotations

import json
import re

from components.ssr import (
    BASE_URL,
    render_episode,
    render_index,
    render_provenance,
    render_season,
    render_sitemap,
    robots_txt,
)


def _episode() -> dict:
    return {
        "id": "s03e15",
        "season": 3,
        "episode": 15,
        "season_episode": "S03E15",
        "title": "Piper Maru",
        "category": "Mythology",
        "air_date": "1996-02-09",
        "label_contested": False,
        "label_fox_dvd": "mythology",
        "label_wikipedia": "mythology",
        "label_dom111": "mythology",
        "label_derived": "mythology",
        "label_rationale": "3 of 3 sources say mythology.",
        "logline": "A salvage diver surfaces changed after a wartime wreck.",
        "logline_generated": "draft",
        "review_status": "human-reviewed",
        "director": ["Rob Bowman"],
        "writers": ["Frank Spotnitz", "Chris Carter"],
        "guest_cast": ["Mitch Pileggi"],
        "imdb_id": "tt0751328",
        "tmdb_movie_id": None,
    }


def _film() -> dict:
    return {
        "id": "film-1998",
        "season": None,
        "episode": None,
        "season_episode": "Film",
        "title": "Fight the Future",
        "category": "Mythology",
        "air_date": "1998-06-19",
        "label_contested": True,
        "label_fox_dvd": "mythology",
        "label_wikipedia": "mythology",
        "label_dom111": None,
        "label_derived": "mythology",
        "label_rationale": "Only 2 sources cover it.",
        "logline": "The partners chase a conspiracy from a Texas cave to Antarctica.",
        "logline_generated": "draft",
        "review_status": "human-reviewed",
        "director": ["Rob Bowman"],
        "writers": ["Chris Carter"],
        "guest_cast": [],
        "imdb_id": "tt0120902",
        "tmdb_movie_id": 10834,
    }


# --- render_episode -------------------------------------------------------


def test_episode_page_carries_the_core_text_in_raw_html():
    html = render_episode(_episode())
    assert "Piper Maru" in html
    assert "Mythology" in html
    assert "salvage diver surfaces changed" in html  # the logline
    assert "1996-02-09" in html
    assert "Rob Bowman" in html and "Frank Spotnitz" in html


def test_episode_page_has_canonical_og_and_jsonld():
    html = render_episode(_episode())
    assert '<link rel="canonical"' in html
    assert f"{BASE_URL}/episode/s03e15" in html
    assert 'property="og:title"' in html
    assert "application/ld+json" in html
    blob = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
    )
    assert blob is not None
    data = json.loads(blob.group(1))
    assert data["@type"] == "TVEpisode"
    assert data["name"] == "Piper Maru"


def test_episode_page_links_out_and_into_the_app():
    html = render_episode(_episode())
    assert "https://www.imdb.com/title/tt0751328/" in html
    assert "themoviedb.org" in html
    assert f"{BASE_URL}/season/3?selected=s03e15" in html  # into the interactive app


def test_film_page_handles_nullable_season_and_links_to_the_app_root():
    html = render_episode(_film())
    assert "Fight the Future" in html
    assert "Film" in html
    assert f'href="{BASE_URL}/"' in html  # a film has no season page in the app


def test_contested_episode_shows_the_per_source_split_and_rationale():
    html = render_episode(_film())  # the film is contested (dom111 abstains)
    assert "no data" in html  # dom111 abstains → rendered as no data
    assert "Only 2 sources cover it." in html


def test_episode_page_ships_no_imagery():
    for record in (_episode(), _film()):
        html = render_episode(record)
        assert "<img" not in html.lower()
        assert "static.tvmaze.com" not in html


def test_episode_page_escapes_html_in_text():
    record = _episode() | {"title": "Tooms & <b>Co</b>"}
    html = render_episode(record)
    assert "Tooms &amp; &lt;b&gt;Co&lt;/b&gt;" in html
    assert "<b>Co</b>" not in html


# --- the other surfaces ---------------------------------------------------


def test_season_page_lists_its_episodes_and_links_to_each():
    html = render_season(3, [_episode()])
    assert "Piper Maru" in html
    assert f"{BASE_URL}/episode/s03e15" in html
    assert f"{BASE_URL}/season/3" in html  # link into the app's season view


def test_season_page_can_list_a_film_row():
    # Films are placed on a season page by air date (matching the app); the
    # renderer must list one when the route passes it in (review finding 5).
    html = render_season(5, [_episode(), _film()])
    assert "Fight the Future" in html
    assert f"{BASE_URL}/episode/film-1998" in html


def test_text_helper_and_render_are_nan_safe():
    # pandas NaN is truthy, so `or ""` would leak the literal 'nan'; _text uses
    # is_missing instead (review finding 2).
    import math

    from components.ssr import _text

    assert _text(math.nan) == ""
    assert _text(None) == ""
    assert _text("S03E15") == "S03E15"
    page = render_episode(_episode() | {"category": math.nan, "season_episode": math.nan})
    assert "Classification: nan" not in page


def test_index_describes_the_project_and_lists_content(episodes_df):
    html = render_index(episodes_df)
    assert "mythology" in html.lower()
    # a real episode title from the sample corpus appears
    assert str(episodes_df.iloc[0]["title"]) in html


def test_provenance_text_page_shows_rederived_numbers(episodes_df):
    html = render_provenance(episodes_df)
    contested = int(episodes_df["label_contested"].sum())
    assert str(contested) in html
    assert "Fox DVDs" in html  # canonical source name


def test_pages_carry_the_attribution_footer():
    for html in (
        render_episode(_episode()),
        render_season(3, [_episode()]),
    ):
        assert "CC BY-SA 4.0" in html
        assert "unofficial fan project" in html


# --- sitemap + robots -----------------------------------------------------


def test_sitemap_lists_every_episode_and_season(episodes_df):
    xml = render_sitemap(episodes_df)
    assert xml.lstrip().startswith("<?xml")
    assert "<urlset" in xml
    first_id = str(episodes_df.iloc[0]["id"])
    assert f"{BASE_URL}/episode/{first_id}" in xml
    assert f"{BASE_URL}/provenance-text" in xml


def test_robots_points_at_the_sitemap():
    text = robots_txt()
    assert "Sitemap:" in text
    assert f"{BASE_URL}/sitemap.xml" in text
