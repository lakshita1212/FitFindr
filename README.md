# FitFindr — AI-Powered Secondhand Shopping & Styling Agent

This project is a multi-tool shopping and styling agent built to search secondhand listings and automatically build outfits using items from a user's existing wardrobe. The backend handles the linear state dependencies and planning loops, while the frontend runs on a Gradio interface.

## Project Structure

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here

To boot up the local Gradio interface, run:
```bash
python app.py
```
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Tool Inventory

The agent utilizes three core modular functions inside `tools.py` to handle the data processing, styling, and text generation steps:

| Tool Name | Input Parameters | Return Type | Core Purpose |
| :--- | :--- | :--- | :--- |
| `search_listings` | `query` (str), `size` (str/None), `max_price` (float/None) | `list[dict]` | Filters down the local `listings.json` file using exact string matches for size/price and basic keyword matching for the query. |
| `suggest_outfit` | `selected_item` (dict), `wardrobe` (list[dict]) | `str` | Calls the `llama-3.3-70b-versatile` LLM to evaluate the discovered item against the user's closet and returns two clear outfit options. |
| `create_fit_card` | `outfit_suggestion` (str), `selected_item` (dict) | `str` | Pipes the outfit ideas and listing details into the LLM to write a punchy, short social media caption optimized for the original marketplace platform. |


## Planning Loop & State Management

The core orchestration loop is managed inside `run_agent()` within `agent.py`. Instead of blindly firing all tools sequentially, the agent tracks execution progress using a centralized `session` state dictionary. This allows us to handle linear data dependencies and trigger early exits when necessary.

### State Flow Logic

1. **Query Parsing:** The user's prompt is processed and passed straight to `search_listings`.
2. **Conditional Branching Guard:** The agent instantly checks the length of the returned listings array:
   * **Empty State (`len(results) == 0`):** The execution loop immediately halts. The agent populates `session["error"]` with contextual tips, leaving all downstream keys as `None` to prevent crash loops.
   * **Valid State (`len(results) > 0`):** The top matching item is extracted and stored inside `session["selected_item"]`.
3. **Styling Invocation:** The agent pulls `session["selected_item"]` and passes it alongside the user's `wardrobe` collection into `suggest_outfit`. The generated text matches are stored in `session["outfit_suggestion"]`.
4. **Caption Generation:** Finally, `session["outfit_suggestion"]` and `session["selected_item"]` are piped into `create_fit_card` to produce a short platform-native caption, which is saved to `session["fit_card"]`.


## Error Handling & Resilience

We added defensive guards at each stage of the pipeline to make sure the app recovers cleanly and surfaces helpful text rather than letting raw Python exceptions break the Gradio UI.

* **Zero Search Results:** If a query yields no items, `search_listings` safely evaluates to `[]` instead of blowing up. The orchestrator catches this empty list and outputs a dynamic suggestion message rather than a generic crash log.
  * *Test Case:* Running `search_listings('designer ballgown', size='XXS', max_price=5)` yields `[]`. The app catches this and prints a clean hint: *"I couldn't find any 'designer ballgown' in size XXS under $5. Try bumping up your budget a bit..."*
* **Empty Closet Fallback:** If a user logs in with an unpopulated closet, `suggest_outfit` catches the empty structural array payload. Instead of failing on key errors, it shifts context to generate general styling advice, color-blocking ideas, and silhouette tips tailored to the type of listing found.
* **Upstream String Safety:** If `suggest_outfit` passes an empty string `""` down to the caption generator due to a text generation timeout or hiccup, `create_fit_card` uses a backup condition to construct a generic social media post using the standalone listing metadata instead of throwing a validation error.

## AI Usage Reflection

I used AI to help speed up writing the code to match the project specs, clean up the phrasing in my planning docs, and debug testing errors. 

Here are two specific ways I used it:

**Writing Spec Code and Planning Docs:**
   * *What I gave it:* I fed it the project specs and my rough notes for how the agent loops should run. It helped me write the initial code structure and reword my planning text so it was clearer.
   * *What I changed:* The AI tended to write code that ran everything sequentially without checking if things failed. I had to manually go in and add strict conditional checks right after the search tool to stop the agent from moving forward if the search results came back empty.

**Debugging Pytest and Terminal Errors:**
   * *What I gave it:* I ran into a bunch of failing pytests and terminal exceptions, like the `NameError` bugs when trying to run chained python commands with semicolons. I pasted the raw tracebacks and terminal outputs into the tool.
   * *What I changed:* It gave me the fixed terminal strings and pointed out where my imports were missing. I didn't just blindly copy it; I verified why the python inline execution string was failing and manually fixed the import statements in my test scripts so the suite would pass.