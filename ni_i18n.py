"""Bangla translation layer for the Streamlit app.

English text in app.py is the lookup key. In Bangla mode, every text-producing
Streamlit call and every HTML block is translated at render time, using
ni_i18n_bn.BN (exact sentences) and the patterns below (sentences that contain
numbers or names). Anything not found stays in English, so a missing
translation never breaks the page.
"""

import re
import unicodedata

import streamlit as st

from ni_i18n_bn import BN

LANG_OPTIONS = ["English", "বাংলা"]

_BENGALI = re.compile(r"[\u0980-\u09FF]")
_LETTERS = re.compile(r"[A-Za-z]{2,}")
_ENTITY = re.compile(r"&\w+;")
_NODE = re.compile(r">([^<>]+)<")
_missing = set()


def _norm(text):
    return unicodedata.normalize("NFKC", text)


_TABLE = {_norm(key): value for key, value in BN.items()}

_NUTRIENT_EN = {
    "energy_kcal": "Energy (kcal)",
    "protein_g": "Protein (g)",
    "fat_g": "Fat (g)",
    "carb_g": "Carbohydrates (g)",
    "fiber_g": "Fiber (g)",
    "sodium_mg": "Sodium (mg)",
    "calcium_mg": "Calcium (mg)",
    "iron_mg": "Iron (mg)",
    "vitamin_a_rae_mcg": "Vitamin A (\u00b5g RAE)",
    "vitamin_c_mg": "Vitamin C (mg)",
    "folate_mcg": "Folate (\u00b5g)",
}


# --------------------------------------------------
# Language state
# --------------------------------------------------

def is_bn():
    return st.session_state.get("lang") == "bn"


def init_language(default):
    if "lang" not in st.session_state:
        st.session_state["lang"] = default if default in ("en", "bn") else "en"


def set_language(code):
    st.session_state["lang"] = "bn" if code == "bn" else "en"


# --------------------------------------------------
# Translation
# --------------------------------------------------

def _unit(unit):
    return "গ্রাম" if unit == "g" else unit


def _lookup(core):
    hit = _TABLE.get(_norm(core))
    if hit is not None:
        return hit
    for regex, build in _PATTERNS:
        match = regex.fullmatch(core)
        if match:
            return build(match)
    return None


def _t(text):
    """Translate a fragment, leaving it unchanged when there is no translation."""
    hit = _lookup(text.strip())
    return text if hit is None else hit


def _exact(text):
    """Exact-sentence lookup only (cheap; used for dropdown option labels)."""
    if not isinstance(text, str):
        return text
    hit = _TABLE.get(_norm(text.strip()))
    return text if hit is None else hit


_AIM = {
    "aim near": "এই বেলার লক্ষ্য প্রায়",
    "at least": "এই বেলায় অন্তত",
    "at most": "এই বেলায় সর্বোচ্চ",
}

_PATTERNS = [
    (re.compile(p), build)
    for p, build in [
        (r"Step (\d+) of (\d+)", lambda m: f"ধাপ {m[1]} / {m[2]}"),
        (r"You're all set, (.+)", lambda m: f"সব প্রস্তুত, {m[1]}"),
        (r"Welcome back, (.+)!", lambda m: f"আবার স্বাগতম, {m[1]}!"),
        (r"AI confidence (\d+%)", lambda m: f"এআই-এর নিশ্চয়তা {m[1]}"),
        (r"Part of (.+)", lambda m: f"{m[1]}-এর অংশ"),
        (r"Closest matches: (.+)", lambda m: f"সবচেয়ে কাছের মিল: {m[1]}"),
        (r"(\d+)% of daily target", lambda m: f"দৈনিক লক্ষ্যের {m[1]}%"),
        (
            r"Difference from target: ([\d,\.]+) (kcal|g)",
            lambda m: f"লক্ষ্য থেকে পার্থক্য: {m[1]} {_unit(m[2])}",
        ),
        (
            r"Meal exceeds the daily estimate by ([\d,\.]+) (kcal|g)\.",
            lambda m: f"এই বেলার খাবার দৈনিক আনুমানিক লক্ষ্যের চেয়ে {m[1]} {_unit(m[2])} বেশি।",
        ),
        (
            r"([\d,\.]+) of ([\d,\.]+) (kcal|g)",
            lambda m: f"{m[2]} {_unit(m[3])}-এর মধ্যে {m[1]}",
        ),
        (
            r"(aim near|at least|at most) ([\d,\.]+) for this meal",
            lambda m: f"{_AIM[m[1]]} {m[2]}",
        ),
        (r"Add ([\d,\.]+) g (.+)", lambda m: f"{m[1]} গ্রাম {m[2]} যোগ করুন"),
        (
            r"Buy ([\d,\.]+) g( from .+)?",
            lambda m: f"{m[1]} গ্রাম কিনুন" + (f" ({m[2][6:]})" if m[2] else ""),
        ),
        (r"([\d,\.]+) BDT", lambda m: f"{m[1]} টাকা"),
        (
            r"(.+?) (\d+%) \u2192 (\d+%)",
            lambda m: f"{_t(m[1])} {m[2]} \u2192 {m[3]}",
        ),
        (r"(Protein|Carbohydrates|Fat) (\d+%)", lambda m: f"{_t(m[1])} {m[2]}"),
        (
            r"(Calories|Protein) comparison unavailable\.",
            lambda m: f"{_t(m[1])}-এর তুলনা পাওয়া যাচ্ছে না।",
        ),
        (
            r"Your (\w+) compared with its share of your daily targets\.",
            lambda m: f"আপনার {_t(m[1].capitalize())} দৈনিক লক্ষ্যের নির্ধারিত অংশের সাথে তুলনা করা হয়েছে।",
        ),
        (
            r"matches your avoid list: (.+)",
            lambda m: f"আপনার এড়িয়ে চলা তালিকার সাথে মিলেছে: {m[1]}",
        ),
        (r"Could not delete the profile: (.+)", lambda m: f"প্রোফাইল মুছে ফেলা যায়নি: {m[1]}"),
        (r"Could not save your profile: (.+)", lambda m: f"প্রোফাইল সংরক্ষণ করা যায়নি: {m[1]}"),
        (r"Could not calculate nutrition: (.+)", lambda m: f"পুষ্টি হিসাব করা যায়নি: {m[1]}"),
        (
            r"(.+) You can add foods manually\.",
            lambda m: f"{_t(m[1])} আপনি নিজে খাবার যোগ করতে পারেন।",
        ),
        (
            r"(\d+) of (\d+) items need your confirmation\.",
            lambda m: f"{m[2]}টির মধ্যে {m[1]}টি আইটেম আপনার নিশ্চিতকরণ দরকার।",
        ),
        (r"Marked out of stock: (.+)", lambda m: f"স্টকে নেই বলে চিহ্নিত: {m[1]}"),
        (
            r"Still low after these add-ons: (.+)",
            lambda m: "এই যোগ করা খাবারের পরও কম থাকছে: "
            + ", ".join(_t(x) for x in m[1].split(", ")),
        ),
        (
            r"Add-ons add about (\d+) kcal\.",
            lambda m: f"এই যোগ করা খাবারে প্রায় {m[1]} kcal যোগ হবে।",
        ),
        (
            r"(.+): (\d+) item\(s\) have no data, so a gap cannot be confirmed\.",
            lambda m: f"{_t(_NUTRIENT_EN.get(m[1], m[1]))}: {m[2]}টি খাবারে তথ্য নেই, তাই ঘাটতি নিশ্চিত করা যায়নি।",
        ),
        (
            r"Connected\. Photo analysis will use (.+)\.",
            lambda m: f"সংযোগ সফল। ছবি বিশ্লেষণে {m[1]} ব্যবহার করা হবে।",
        ),
    ]
]


def _translate(text, log):
    if not isinstance(text, str) or not _LETTERS.search(_ENTITY.sub("", text)):
        return text
    core = text.strip()
    hit = _lookup(core)
    if hit is None:
        if log and not _BENGALI.search(core):
            _missing.add(core)
        return text
    start = len(text) - len(text.lstrip())
    end = len(text.rstrip())
    return text[:start] + hit + text[end:]


def tr(text):
    """Translate one string when the interface is in Bangla."""
    return _translate(text, True) if is_bn() else text


def tr_html(markup):
    """Translate the text between tags of an HTML block (tags are untouched)."""
    if not is_bn() or not isinstance(markup, str):
        return markup
    whole = _TABLE.get(_norm(markup.strip()))
    if whole is not None:
        return whole
    return _NODE.sub(lambda m: ">" + _translate(m.group(1), False) + "<", markup)


# --------------------------------------------------
# Streamlit wrappers
# --------------------------------------------------

_ARG0_TEXT = [
    "subheader", "header", "title", "caption", "warning", "error", "info",
    "success", "button", "form_submit_button", "toggle", "checkbox",
    "text_input", "number_input", "selectbox", "radio", "multiselect",
    "expander", "spinner", "text_area",
]
_CHOICE = {"selectbox", "radio", "multiselect"}
_WRAPPED = _ARG0_TEXT + ["write", "markdown", "image", "tabs"]


def _make(name, original):
    def wrapper(*args, **kwargs):
        if is_bn():
            args = list(args)
            if name in _ARG0_TEXT and args:
                args[0] = tr(args[0])
            elif name == "write":
                args = [tr(a) for a in args]
            elif name == "markdown" and args and not kwargs.get("unsafe_allow_html"):
                args[0] = tr(args[0])
            elif name == "tabs" and args:
                args[0] = [tr(x) for x in args[0]]
            for key in ("body", "label", "text", "help", "placeholder", "caption"):
                if isinstance(kwargs.get(key), str):
                    kwargs[key] = tr(kwargs[key])
            if name in _CHOICE:
                inner = kwargs.get("format_func")
                kwargs["format_func"] = lambda v, _f=inner: _exact(_f(v) if _f else str(v))
        return original(*args, **kwargs)

    return wrapper


def install():
    """Wrap Streamlit's text calls. Safe to call on every rerun."""
    originals = st.__dict__.setdefault("_ni_originals", {})
    for name in _WRAPPED:
        if not hasattr(st, name):
            continue
        original = originals.setdefault(name, getattr(st, name))
        setattr(st, name, _make(name, original))


def show_missing():
    """Developer aid (NI_DEV=1): list strings that had no Bangla translation."""
    if not _missing:
        return
    expander = st.__dict__.get("_ni_originals", {}).get("expander", st.expander)
    with st.sidebar:
        with expander("Untranslated strings (dev)"):
            st.code("\n".join(sorted(_missing)))
