"""
ai_service.py
-------------
AI functionality for LastBite using GPT-4o Vision (OpenAI).

GPT-4o Vision can look at a fridge photo and accurately identify every
food item with realistic quantities. It also generates tailored recipe
suggestions based on actual pantry contents.

The API key is loaded from the .env file — never hardcoded in the code.
"""

import json
import os
import re

from openai import AsyncOpenAI

# Load API key from .env file
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ── Food categories ────────────────────────────────────────────────────────────

FOOD_CATEGORIES = {
    "apple": "fruit", "banana": "fruit", "orange": "fruit", "lemon": "fruit",
    "lime": "fruit", "strawberry": "fruit", "blueberry": "fruit", "grape": "fruit",
    "mango": "fruit", "avocado": "fruit", "watermelon": "fruit", "peach": "fruit",
    "pear": "fruit", "cherry": "fruit",
    "milk": "dairy", "cheese": "dairy", "butter": "dairy",
    "yogurt": "dairy", "cream": "dairy",
    "egg": "protein", "eggs": "protein", "chicken": "protein", "beef": "protein",
    "fish": "protein", "salmon": "protein", "shrimp": "protein",
    "sausage": "protein", "tofu": "protein",
    "bread": "grain", "rice": "grain", "pasta": "grain",
    "flour": "grain", "oats": "grain", "tortilla": "grain",
    "potato": "vegetable", "carrot": "vegetable", "tomato": "vegetable",
    "onion": "vegetable", "garlic": "vegetable", "spinach": "vegetable",
    "lettuce": "vegetable", "broccoli": "vegetable", "pepper": "vegetable",
    "mushroom": "vegetable", "cucumber": "vegetable", "corn": "vegetable",
    "celery": "vegetable", "zucchini": "vegetable", "kale": "vegetable",
    "cauliflower": "vegetable", "cabbage": "vegetable", "eggplant": "vegetable",
    "ketchup": "condiment", "mustard": "condiment", "olive oil": "condiment",
    "soy sauce": "condiment", "honey": "condiment", "mayonnaise": "condiment",
    "hot sauce": "condiment", "vinegar": "condiment",
}


# ── Recipe database (fallback) ─────────────────────────────────────────────────

RECIPE_DB = [
    {
        "name": "Scrambled Eggs",
        "required": ["egg"],
        "optional": ["butter", "milk", "cheese"],
        "description": "Classic fluffy scrambled eggs.",
        "time_minutes": 8,
        "steps": [
            "Crack eggs into a bowl and whisk with a splash of milk.",
            "Melt butter in a pan over low heat.",
            "Pour in eggs, stir gently until just set.",
            "Season with salt and pepper.",
        ],
    },
    {
        "name": "Pasta with Tomato Sauce",
        "required": ["pasta", "tomato"],
        "optional": ["onion", "garlic", "cheese", "olive oil"],
        "description": "Simple homemade tomato pasta.",
        "time_minutes": 20,
        "steps": [
            "Cook pasta according to package instructions.",
            "Sauté garlic and onion in olive oil.",
            "Add chopped tomatoes and simmer 10 minutes.",
            "Toss pasta in sauce and top with cheese.",
        ],
    },
    {
        "name": "Chicken Stir Fry",
        "required": ["chicken"],
        "optional": ["pepper", "onion", "garlic", "broccoli", "soy sauce", "rice"],
        "description": "Quick pan-fried chicken with vegetables.",
        "time_minutes": 20,
        "steps": [
            "Slice chicken into thin strips.",
            "Cook chicken in a hot pan until golden, set aside.",
            "Stir fry vegetables 3 minutes, add chicken back.",
            "Season with soy sauce and serve over rice.",
        ],
    },
    {
        "name": "Greek Salad",
        "required": ["tomato", "cucumber"],
        "optional": ["onion", "cheese", "olive oil", "pepper"],
        "description": "Fresh Mediterranean salad.",
        "time_minutes": 10,
        "steps": [
            "Chop tomatoes, cucumber, and onion.",
            "Combine with crumbled cheese.",
            "Drizzle with olive oil and season to taste.",
        ],
    },
    {
        "name": "Vegetable Omelette",
        "required": ["egg"],
        "optional": ["spinach", "tomato", "pepper", "mushroom", "cheese", "butter"],
        "description": "Fluffy omelette with fresh vegetables.",
        "time_minutes": 12,
        "steps": [
            "Beat eggs with salt and pepper.",
            "Sauté vegetables in butter until soft.",
            "Pour eggs over vegetables and cook until set.",
            "Fold and serve.",
        ],
    },
    {
        "name": "Fried Rice",
        "required": ["rice"],
        "optional": ["egg", "onion", "garlic", "carrot", "soy sauce"],
        "description": "Classic fried rice with pantry staples.",
        "time_minutes": 15,
        "steps": [
            "Stir fry onion and garlic in oil.",
            "Push aside and scramble an egg.",
            "Add rice and soy sauce, toss everything together.",
        ],
    },
    {
        "name": "Avocado Toast",
        "required": ["avocado", "bread"],
        "optional": ["egg", "tomato", "lemon"],
        "description": "Creamy avocado on crispy toast.",
        "time_minutes": 8,
        "steps": [
            "Toast bread until crispy.",
            "Mash avocado with lemon, salt and pepper.",
            "Spread on toast and top with sliced tomato or a fried egg.",
        ],
    },
]


# ── Helper ─────────────────────────────────────────────────────────────────────

def parse_json_array(text: str) -> list:
    """Extract and parse a JSON array from a text response."""
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return []


# ── Food scanning ──────────────────────────────────────────────────────────────

async def scan_image_for_food(image_b64: str, content_type: str) -> list[dict]:
    """
    Detect food items and quantities from a photo using GPT-4o Vision.

    GPT-4o looks at the actual image and identifies every food item it sees,
    counting quantities accurately (e.g. 12 eggs in a carton, 6 lemons).

    Returns a list of dicts with 'name', 'quantity', and 'category'.
    """

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{content_type};base64,{image_b64}",
                        "detail": "high",
                    },
                },
                {
                    "type": "text",
                    "text": """Look carefully at this fridge/pantry image.
Identify every food item you can see and count the real quantity.

Examples of good quantity detection:
- A full egg carton = 12 eggs
- A pile of lemons = count them individually
- A bottle of ketchup = 1

Reply with ONLY a JSON array, no explanation.
Format: [{"name": "egg", "quantity": 12}, {"name": "lemon", "quantity": 6}]

Rules:
- Use simple singular English names (egg not eggs)
- quantity must be a whole number
- Only include items clearly visible"""
                },
            ],
        }],
        max_tokens=600,
    )

    raw = response.choices[0].message.content.strip()
    items = parse_json_array(raw)

    # Build structured list, skipping duplicates
    detected = []
    seen: set[str] = set()
    for item in items:
        name = str(item.get("name", "")).strip().lower()
        qty  = str(item.get("quantity", "1"))
        if not name or name in seen:
            continue
        seen.add(name)
        detected.append({
            "name":     name,
            "quantity": qty,
            "category": FOOD_CATEGORIES.get(name, "other"),
        })

    return detected


# ── Recipe suggestions ─────────────────────────────────────────────────────────

async def get_recipe_suggestions(ingredients: list[dict]) -> list[dict]:
    """
    Generate recipe suggestions using GPT-4o based on pantry contents.

    GPT-4o receives the ingredient list with expiry info and suggests
    5 practical recipes, prioritising ingredients expiring soon.

    Falls back to the built-in recipe database if the API call fails.
    """

    ingredient_list = ", ".join(
        f"{i['name']} (x{i['quantity']}, {i['days_remaining']}d left)"
        for i in sorted(ingredients, key=lambda x: x["days_remaining"])
    )

    expiring = [i["name"] for i in ingredients if i["days_remaining"] <= 3]
    expiry_note = f"\nIMPORTANT: Use these soon — {', '.join(expiring)}." if expiring else ""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": f"""I have these ingredients: {ingredient_list}{expiry_note}

Suggest 5 practical recipes using only these ingredients.
Reply with ONLY a JSON array, no explanation.

Format:
[{{
  "name": "Recipe Name",
  "description": "One sentence.",
  "time_minutes": 15,
  "priority_reason": "Why to cook this now.",
  "ingredients_used": ["ingredient1", "ingredient2"],
  "steps": ["Step 1.", "Step 2.", "Step 3."]
}}]"""
        }],
        max_tokens=1500,
    )

    raw = response.choices[0].message.content.strip()
    recipes = parse_json_array(raw)

    if recipes:
        return [
            {
                "name":             r.get("name", "Recipe"),
                "description":      r.get("description", ""),
                "time_minutes":     r.get("time_minutes", 20),
                "priority_reason":  r.get("priority_reason", "Good use of your ingredients."),
                "ingredients_used": r.get("ingredients_used", []),
                "steps":            r.get("steps", []),
            }
            for r in recipes[:5]
        ]

    return _fallback_recipes(ingredients)


def _fallback_recipes(ingredients: list[dict]) -> list[dict]:
    """Rule-based fallback if GPT-4o response cannot be parsed."""
    available = {i["name"].lower() for i in ingredients if i["days_remaining"] > 0}
    expiring  = [i["name"] for i in ingredients if 0 < i["days_remaining"] <= 5]

    scored = []
    for recipe in RECIPE_DB:
        if not set(recipe["required"]).issubset(available):
            continue
        score = len(set(recipe["optional"]) & available)
        scored.append((score, recipe))

    scored.sort(reverse=True)
    result = []
    for _, r in scored[:5]:
        uses_expiring = [n for n in expiring if n in r["required"] + r["optional"]]
        priority = f"Uses {uses_expiring[0]} expiring soon!" if uses_expiring else "Good use of your ingredients."
        result.append({**r, "priority_reason": priority, "ingredients_used": r["required"] + r["optional"]})
    return result
