"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── query parser ──────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract description, size, and max_price from a natural language query
    using regex and string processing.

    Examples:
        "vintage graphic tee under $30, size M"
          → {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}

        "looking for a floral dress"
          → {"description": "floral dress", "size": None, "max_price": None}
    """
    # --- Extract max_price ---
    # Matches patterns like: "under $30", "under 30", "max $25.99", "$30 or less"
    price_match = re.search(
        r"(?:under|below|max(?:imum)?|less than|up to|no more than)\s*\$?\s*(\d+(?:\.\d+)?)"
        r"|\$\s*(\d+(?:\.\d+)?)\s*(?:or less|max|maximum)",
        query,
        re.IGNORECASE,
    )
    max_price = None
    if price_match:
        raw = price_match.group(1) or price_match.group(2)
        max_price = float(raw)

    # --- Extract size ---
    # Matches: "size M", "size XL", standalone S/M/L/XL/XXS/XXL etc.
    size_match = re.search(
        r"\bsize\s+([A-Z]{1,3}(?:/[A-Z]{1,3})?)\b"
        r"|\b(XXS|XS|S|M|L|XL|XXL|XXXL)\b",
        query,
        re.IGNORECASE,
    )
    size = None
    if size_match:
        size = (size_match.group(1) or size_match.group(2)).upper()

    # --- Extract description ---
    # Remove the price and size fragments to leave clean keywords
    description = query
    if price_match:
        description = description[:price_match.start()] + description[price_match.end():]
    if size_match:
        description = description[:size_match.start()] + description[size_match.end():]

    # Strip common filler phrases and punctuation, then collapse whitespace
    filler = re.compile(
        r"\b(looking for|i want|i need|find me|searching for|a|an|the)\b",
        re.IGNORECASE,
    )
    description = filler.sub(" ", description)
    description = re.sub(r"[,;]+", " ", description)
    description = " ".join(description.split()).strip()

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.
    """

    # ── Step 1: Initialize session ────────────────────────────────────────────
    session = _new_session(query, wardrobe)

    # ── Step 2: Parse the query ───────────────────────────────────────────────
    session["parsed"] = _parse_query(query)

    description = session["parsed"]["description"]
    size        = session["parsed"]["size"]
    max_price   = session["parsed"]["max_price"]

    # ── Step 3: Search listings ───────────────────────────────────────────────
    session["search_results"] = search_listings(
        description=description,
        size=size,
        max_price=max_price,
    )

    # ── Conditional branch: halt early if no results ──────────────────────────
    if not session["search_results"]:
        price_hint = f" under ${max_price:.0f}" if max_price else ""
        size_hint  = f" in size {size}" if size else ""
        session["error"] = (
            f"I couldn't find any '{description}'{size_hint}{price_hint}. "
            "Try bumping up your budget a bit, removing the size filter, "
            "or using broader keywords — for example 'retro tee' instead of "
            "'vintage 90s band tee'."
        )
        return session

    # ── Step 4: Select the top result ─────────────────────────────────────────
    session["selected_item"] = session["search_results"][0]

    # ── Step 5: Suggest an outfit ─────────────────────────────────────────────
    session["outfit_suggestion"] = suggest_outfit(
        new_item=session["selected_item"],
        wardrobe=session["wardrobe"],
    )

    # ── Step 6: Generate the fit card caption ─────────────────────────────────
    session["fit_card"] = create_fit_card(
        outfit=session["outfit_suggestion"],
        new_item=session["selected_item"],
    )

    # ── Step 7: Return the fully populated session ────────────────────────────
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")