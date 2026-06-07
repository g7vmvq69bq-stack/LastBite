"""
freshness.py
------------
Defines how long each food item stays fresh (in days) and calculates
the survival runway — how many days of meals the user can make from
their current pantry.
"""

# ── Freshness dictionary ───────────────────────────────────────────────────────
# Maps food names to how many days they stay fresh after being added to the pantry.
# These values assume the food was just bought / is in the fridge.

FRESHNESS_DAYS: dict[str, int] = {
    # Proteins — short shelf life, must be used quickly
    "egg": 21, "eggs": 21,
    "chicken": 2, "beef": 3, "pork": 3, "fish": 2,
    "salmon": 2, "shrimp": 2, "turkey": 2, "lamb": 3, "tofu": 5,
    "tuna": 2, "crab": 2, "lobster": 2, "sausage": 3,

    # Dairy — medium shelf life
    "milk": 7, "cheese": 14, "butter": 30, "yogurt": 14,
    "cream": 7, "sour cream": 14, "cream cheese": 14,
    "cottage cheese": 7, "heavy cream": 7, "half and half": 10,

    # Vegetables — varies widely by type
    "lettuce": 5, "spinach": 5, "kale": 7, "arugula": 5,
    "carrot": 14, "carrots": 14, "broccoli": 5, "cauliflower": 7,
    "tomato": 7, "tomatoes": 7, "cucumber": 7, "zucchini": 7,
    "pepper": 7, "peppers": 7, "bell pepper": 7,
    "onion": 30, "onions": 30, "garlic": 30,
    "potato": 30, "potatoes": 30, "sweet potato": 21,
    "corn": 3, "peas": 3, "green beans": 5, "asparagus": 4,
    "mushroom": 5, "mushrooms": 5, "celery": 14, "cabbage": 14,
    "eggplant": 7, "beet": 14, "beets": 14, "radish": 7,

    # Fruits — most last under a week
    "apple": 21, "apples": 21, "banana": 5, "bananas": 5,
    "orange": 14, "oranges": 14, "lemon": 14, "lime": 14,
    "strawberry": 5, "strawberries": 5, "blueberries": 7,
    "grapes": 7, "mango": 5, "peach": 5, "pear": 7,
    "avocado": 3, "watermelon": 5, "pineapple": 5,

    # Grains and pantry staples — long shelf life
    "bread": 7, "rice": 180, "pasta": 180, "flour": 180,
    "oats": 180, "cereal": 90, "crackers": 30, "tortilla": 7,
    "noodles": 180, "quinoa": 365,

    # Condiments — very long shelf life
    "sugar": 365, "salt": 999, "oil": 180, "olive oil": 180,
    "vinegar": 365, "soy sauce": 365, "ketchup": 90,
    "mustard": 90, "hot sauce": 180, "honey": 999,
    "mayonnaise": 14,
}

# If a food is not in the dictionary above, assume 7 days as a safe default
DEFAULT_FRESHNESS = 7


# ── Meal contribution per food category ───────────────────────────────────────
# Defines how many meals one unit of a food category contributes.
# For example, one chicken breast (protein) provides 2 meals,
# while one apple (fruit) only provides 0.25 of a meal.

CATEGORY_MEAL_CONTRIBUTION: dict[str, float] = {
    "protein":   2.0,   # Meat, eggs, fish — filling main courses
    "grain":     3.0,   # Rice, pasta, bread — high volume staples
    "dairy":     1.0,   # Milk, cheese, yogurt — side/supplement
    "vegetable": 0.75,  # Vegetables — sides, not enough alone
    "fruit":     0.25,  # Fruits — snacks, not full meals
    "condiment": 0.0,   # Sauces and oils — do not count as meals
    "beverage":  0.0,   # Drinks — do not count
    "other":     0.5,   # Unknown category — conservative estimate
}


def get_freshness_days(food_name: str) -> int:
    """
    Look up how many days a food item stays fresh.

    First tries an exact match, then a partial match (e.g. 'cherry tomatoes'
    will match 'tomato'). Falls back to DEFAULT_FRESHNESS if nothing is found.
    """
    name = food_name.lower().strip()

    # Exact match
    if name in FRESHNESS_DAYS:
        return FRESHNESS_DAYS[name]

    # Partial match — handles plurals and compound names
    for key, days in FRESHNESS_DAYS.items():
        if key in name or name in key:
            return days

    # Nothing matched — use a safe default
    return DEFAULT_FRESHNESS


def calculate_survival_runway(items: list[dict]) -> dict:
    """
    Calculate how many days the user can survive on their current pantry.

    Each non-expired item contributes a number of meals based on its category.
    Total meals divided by 3 (meals per day) gives the survival days.

    Returns a summary dict with:
    - total_meals: total estimated meals from all items
    - survival_days: total_meals / 3
    - item_count: number of non-expired items
    - breakdown: meal contribution per item, sorted by expiry
    - critical_items: items expiring within 3 days
    """
    # Only count items that have not expired yet
    available = [i for i in items if i["days_remaining"] > 0]

    if not available:
        return {
            "total_meals": 0,
            "survival_days": 0,
            "daily_meals": 3,
            "item_count": 0,
            "breakdown": [],
            "critical_items": [],
        }

    total_meals = 0.0
    breakdown = []

    for item in available:
        # Look up how many meals this category contributes
        contribution = CATEGORY_MEAL_CONTRIBUTION.get(item.get("category", "other"), 0.5)

        if contribution > 0:
            total_meals += contribution
            breakdown.append({
                "name": item["name"],
                "meals": contribution,
                "days_remaining": item["days_remaining"],
            })

    # Assume 3 meals per day to convert total meals into days
    daily_meals = 3
    survival_days = round(total_meals / daily_meals, 1)

    # Critical items = expiring within 3 days, sorted by most urgent first
    critical = sorted(
        [i for i in available if i["days_remaining"] <= 3],
        key=lambda x: x["days_remaining"],
    )

    return {
        "total_meals": round(total_meals, 1),
        "survival_days": survival_days,
        "daily_meals": daily_meals,
        "item_count": len(available),
        "breakdown": sorted(breakdown, key=lambda x: x["days_remaining"]),
        "critical_items": critical[:5],  # Show up to 5 most urgent
    }
