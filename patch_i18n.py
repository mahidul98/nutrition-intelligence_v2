"""One-time patch: wire the Bangla layer and the new food-name columns into app.py.

Run from the project folder:  python patch_i18n.py
Every edit must match exactly once, otherwise nothing is saved.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"

for needed in ("ni_i18n.py", "ni_i18n_bn.py"):
    if not (ROOT / needed).exists():
        raise SystemExit(needed + " is missing from " + str(ROOT) + ". Nothing was changed.")

text = APP.read_bytes().decode("utf-8")
nl = "\r\n" if "\r\n" in text else "\n"


def fx(s):
    return s.replace("\n", nl)


HELPERS = '''esc = html.escape

install()


@lru_cache(maxsize=1)
def _food_table():
    """code -> (clean English name, Bangla name) from the foods table."""
    df = load_foods()
    en_col = "display_name_en" if "display_name_en" in df.columns else "name_en"
    bn_values = df["name_bn"].astype(str) if "name_bn" in df.columns else [""] * len(df)
    table = {}
    for code, en, bn in zip(df["code"].astype(str), df[en_col].astype(str), bn_values):
        bn = "" if bn.lower() == "nan" else bn.strip()
        table[code] = (en.strip(), bn)
    return table


def food_name(code, fallback=""):
    """Clean food name in the current language (Bangla script in Bangla mode)."""
    en, bn = _food_table().get(str(code), (str(fallback), ""))
    return (bn if is_bn() and bn else en) or str(fallback)


def food_option_label(code):
    """Dropdown label showing both languages, so search works in either."""
    en, bn = _food_table().get(str(code), (str(code), ""))
    if not bn:
        return en
    return f"{bn} ({en})" if is_bn() else f"{en} ({bn})"


def item_title(candidate, matched):
    """Name on a review card: the Bangla name of a matched food in Bangla mode."""
    if matched and is_bn():
        return food_name(candidate.fct_code, str(candidate.detected_name))
    return str(candidate.detected_name)


def diet_conflict_text(conflict):
    name = md_safe(food_name(conflict.fct_code, conflict.name_en))
    return f"{tr('Diet conflict:')} {name} {tr(conflict.reason)}."
'''

THEME_END = '''        pass  # the choice still applies for this session


def on_language_change(widget_key):
    """Switch the interface language and remember the choice in the saved profile."""
    set_language("bn" if st.session_state.get(widget_key) == LANG_OPTIONS[1] else "en")
    current = load_user_profile()
    if current is None:
        return
    current["lang"] = st.session_state["lang"]
    try:
        save_user_profile(current)
    except OSError:
        pass  # the choice still applies for this session


def language_picker(key):
    st.radio(
        "Language",
        LANG_OPTIONS,
        index=1 if is_bn() else 0,
        horizontal=True,
        key=key,
        on_change=on_language_change,
        args=(key,),
        label_visibility="collapsed",
    )
'''

edits = [
    # 1. import the translation layer
    (
        "from backend.app.service import run_report\n",
        "from backend.app.service import run_report\n"
        "from ni_i18n import (\n"
        "    LANG_OPTIONS,\n"
        "    init_language,\n"
        "    install,\n"
        "    is_bn,\n"
        "    set_language,\n"
        "    show_missing,\n"
        "    tr,\n"
        "    tr_html,\n"
        ")\n",
    ),
    # 2. food-name helpers + install the wrappers
    ("esc = html.escape\n", HELPERS),
    # 3. language switch callback and picker
    ("        pass  # the choice still applies for this session\n", THEME_END),
    # 4. HTML blocks are translated
    (
        "    st.markdown(markup, unsafe_allow_html=True)\n",
        "    st.markdown(tr_html(markup), unsafe_allow_html=True)\n",
    ),
    # 5. language picker on the first-time setup page
    (
        '    with middle:\n        html_block(\n            hero_html(\n                "Welcome to Nutrition Intelligence",',
        '    with middle:\n        language_picker("lang_pick_onboarding")\n        html_block(\n            hero_html(\n                "Welcome to Nutrition Intelligence",',
    ),
    # 6. remember the language when the profile is first saved
    (
        "save_user_profile(saved)",
        'save_user_profile({**saved, "lang": st.session_state.get("lang", "en")})',
    ),
    # 7. start in the saved language
    (
        "raw_profile = load_user_profile()\n",
        "raw_profile = load_user_profile()\n"
        'init_language((raw_profile or {}).get("lang", "en"))\n',
    ),
    # 8. language picker in the sidebar
    (
        '    st.toggle("Dark mode", key="dark_mode_toggle", on_change=save_theme_choice)\n',
        '    language_picker("lang_pick_sidebar")\n'
        '    st.toggle("Dark mode", key="dark_mode_toggle", on_change=save_theme_choice)\n',
    ),
    # 9. keep the language when the profile is edited
    (
        '"dark_mode": profile["dark_mode"],',
        '"dark_mode": profile["dark_mode"],\n'
        '                    "lang": st.session_state.get("lang", "en"),',
    ),
    # 10. food dropdown labels use the clean names in both languages
    (
        "    food_labels = {\n"
        "        code: food_label(name, bn)\n"
        "        for code, name, bn in zip(\n"
        '            food_codes, foods_df["name_en"].astype(str).tolist(), bn_names\n'
        "        )\n"
        "    }",
        "    food_labels = {code: food_option_label(code) for code in food_codes}",
    ),
    # 11. review card title
    (
        "{esc(str(candidate.detected_name))}</span>'",
        "{esc(item_title(candidate, matched))}</span>'",
    ),
    # 12. closest-match names
    (
        'esc(a["name_en"]) for a in candidate.alternatives',
        'esc(food_name(a["code"], a["name_en"])) for a in candidate.alternatives',
    ),
    # 13. add-on names
    (
        "g {esc(item.name_en)}'",
        "g {esc(food_name(item.fct_code, item.name_en))}'",
    ),
    # 14. diet conflict message
    (
        'st.warning(f"Diet conflict: {md_safe(conflict.name_en)} {conflict.reason}.")',
        "st.warning(diet_conflict_text(conflict))",
    ),
    # 15. out-of-stock names
    (
        "names = {item.name_en: item.fct_code for item in pivot.items}",
        "names = {\n"
        "                food_name(item.fct_code, item.name_en): item.fct_code\n"
        "                for item in pivot.items\n"
        "            }",
    ),
    # 16. out-of-stock caption shows names, not codes
    (
        '+ ", ".join(st.session_state["out_of_stock"])',
        '+ ", ".join(food_name(c) for c in st.session_state["out_of_stock"])',
    ),
    # 17. foods-used table
    (
        "line.name_en,",
        'food_name(getattr(line, "fct_code", ""), line.name_en),',
    ),
    # 18. progress indicator is translated; developer list of missing strings
    (
        "stepper_slot.markdown(\n"
        "    f'<div class=\"stepper\">{\"\".join(steps_html)}</div>', unsafe_allow_html=True\n"
        ")",
        "stepper_slot.markdown(\n"
        "    tr_html(f'<div class=\"stepper\">{\"\".join(steps_html)}</div>'),\n"
        "    unsafe_allow_html=True,\n"
        ")\n"
        "\n"
        'if os.getenv("NI_DEV"):\n'
        "    show_missing()",
    ),
]

for old, new in edits:
    count = text.count(fx(old))
    print(count, "x", fx(old)[:60].replace(nl, " "))
    if count != 1:
        raise SystemExit("Expected exactly one match. Nothing was saved.")

for old, new in edits:
    text = text.replace(fx(old), fx(new))

APP.write_bytes(text.encode("utf-8"))
print("Saved", APP, "(" + str(len(edits)) + " edits)")
