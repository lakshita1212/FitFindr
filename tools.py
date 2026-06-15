"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches.
    """
    listings = load_listings()

    # Step 1: Filter by max_price and size
    filtered = []
    for item in listings:
        if max_price is not None and item.get("price", 0) > max_price:
            continue
        if size is not None:
            item_size = item.get("size", "").lower()
            if size.lower() not in item_size:
                continue
        filtered.append(item)

    # Step 2: Score by keyword overlap with description
    keywords = description.lower().split()

    def score(item):
        # Fields to search across
        # Force a blank string if any field returns None
        searchable = " ".join([
            item.get("title") or "",
            item.get("description") or "",
            item.get("category") or "",
            item.get("brand") or "",
            " ".join(item.get("style_tags") or []),
            " ".join(item.get("colors") or []),
        ]).lower()

        return sum(1 for kw in keywords if kw in searchable)

    scored = [(item, score(item)) for item in filtered]

    # Step 3: Drop zero-score items and sort highest first
    matched = [(item, s) for item, s in scored if s > 0]
    matched.sort(key=lambda x: x[1], reverse=True)

    return [item for item, _ in matched]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty.

    Returns:
        A non-empty string with outfit suggestions.
    """
    client = _get_groq_client()

    item_summary = (
        f"Item: {new_item.get('title', 'Unknown')}\n"
        f"Category: {new_item.get('category', 'N/A')}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"Colors: {', '.join(new_item.get('colors', []))}\n"
        f"Brand: {new_item.get('brand', 'N/A')}\n"
        f"Condition: {new_item.get('condition', 'N/A')}"
    )

    wardrobe_items = wardrobe.get("items", [])

    if not wardrobe_items:
        # Empty wardrobe: give general styling advice
        prompt = (
            f"A user just thrifted this item:\n{item_summary}\n\n"
            "Their wardrobe is currently empty. Suggest 1–2 outfit ideas using "
            "classic wardrobe staples (like raw denim, white tees, clean sneakers, "
            "neutral trousers) that would pair well with this piece. "
            "Be specific about the vibe and keep the tone casual and friendly."
        )
    else:
        # Format the wardrobe for the prompt
        wardrobe_lines = []
        for i, w_item in enumerate(wardrobe_items, 1):
            wardrobe_lines.append(
                f"{i}. {w_item.get('title', 'Unknown')} "
                f"({w_item.get('category', 'N/A')}, "
                f"{', '.join(w_item.get('colors', []))})"
            )
        wardrobe_summary = "\n".join(wardrobe_lines)

        prompt = (
            f"A user just thrifted this item:\n{item_summary}\n\n"
            f"Their current wardrobe includes:\n{wardrobe_summary}\n\n"
            "Suggest 1–2 complete outfit combinations using the new item and "
            "specific pieces from their wardrobe. Name the wardrobe pieces by title. "
            "Be specific about the overall vibe and keep the tone casual and friendly."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
    """
    # Guard against empty outfit input
    if not outfit or not outfit.strip():
        title = new_item.get("title", "this find")
        price = new_item.get("price", "?")
        platform = new_item.get("platform", "a thrift app")
        return (
            f"Looks like the outfit generator hit a snag, but here's a quick post "
            f"for your new find: 'Just copped this {title} for ${price} on "
            f"{platform}! 🛒✨'"
        )

    client = _get_groq_client()

    title = new_item.get("title", "Unknown item")
    price = new_item.get("price", "N/A")
    platform = new_item.get("platform", "a thrift app")
    style_tags = ", ".join(new_item.get("style_tags", []))

    prompt = (
        f"Write a 2–4 sentence Instagram/TikTok caption for this thrifted outfit.\n\n"
        f"New thrifted item: {title} (${price} from {platform})\n"
        f"Style tags: {style_tags}\n"
        f"Outfit idea: {outfit}\n\n"
        "Guidelines:\n"
        "- Sound casual and authentic, like a real OOTD post — not a product description\n"
        "- Mention the item name, price, and platform naturally, each only once\n"
        "- Capture the outfit vibe in specific, evocative terms\n"
        "- Include 1–3 relevant emojis\n"
        "- Do NOT use hashtags\n"
        "Return only the caption text, nothing else."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.95,  # Higher temperature for variety
    )

    return response.choices[0].message.content.strip()