from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


VALID_SKIN_TYPES = {"oily", "dry", "combination", "sensitive", "normal", "acne_prone"}
VALID_CONCERNS = {
    "acne",
    "blackheads",
    "excess_oil",
    "dryness",
    "sensitivity",
    "redness",
    "rosacea",
    "hyperpigmentation",
    "dark_spots",
    "dullness",
    "fine_lines",
    "wrinkles",
    "texture",
    "pores",
    "sun_damage",
    "dark_circles",
    "puffiness",
}
VALID_ALLERGIES = {
    "fragrance",
    "essential_oils",
    "salicylic_acid",
    "retinol",
    "vitamin_c",
    "niacinamide",
    "alcohol",
    "sulfates",
    "parabens",
    "coconut_oil",
    "lanolin",
    "latex",
}
VALID_AGE_RANGES = {"teens", "20s", "30s", "40s", "50s", "60+"}
VALID_CLIMATES = {"humid", "dry", "temperate", "cold", "tropical"}
VALID_BUDGETS = {"budget", "mid", "premium", "any"}

ALLERGY_TERMS = {
    "fragrance": ["fragrance", "parfum"],
    "essential_oils": ["essential oil", "limonene", "linalool", "citral", "eucalyptus", "lavender"],
    "salicylic_acid": ["salicylic acid"],
    "retinol": ["retinol", "retinal", "retinyl"],
    "vitamin_c": ["ascorbic acid", "vitamin c", "tetrahexyldecyl ascorbate"],
    "niacinamide": ["niacinamide", "niacin"],
    "alcohol": ["alcohol denat", "sd alcohol", "ethanol"],
    "sulfates": ["sulfate", "sulphate"],
    "parabens": ["paraben"],
    "coconut_oil": ["cocos nucifera", "coconut"],
    "lanolin": ["lanolin"],
    "latex": ["latex"],
}


@dataclass
class UserProfile:
    skin_type: str
    concerns: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    age_range: str = "30s"
    climate: str = "temperate"
    budget: str = "any"
    pregnancy: bool = False
    sensitivity_level: str = "normal"

    def __post_init__(self) -> None:
        if self.skin_type not in VALID_SKIN_TYPES:
            raise ValueError(f"Invalid skin_type: {self.skin_type}")
        self.concerns = _clean_values(self.concerns, VALID_CONCERNS, "concern")
        self.allergies = _clean_values(self.allergies, VALID_ALLERGIES, "allergy")
        if self.age_range not in VALID_AGE_RANGES:
            raise ValueError(f"Invalid age_range: {self.age_range}")
        if self.climate not in VALID_CLIMATES:
            raise ValueError(f"Invalid climate: {self.climate}")
        if self.budget not in VALID_BUDGETS:
            raise ValueError(f"Invalid budget: {self.budget}")
        if self.sensitivity_level not in {"low", "normal", "high"}:
            raise ValueError(f"Invalid sensitivity_level: {self.sensitivity_level}")

    @property
    def effective_concerns(self) -> list[str]:
        concerns = set(self.concerns)
        if self.skin_type in {"oily", "acne_prone"}:
            concerns.update({"excess_oil", "pores"})
        if self.skin_type == "dry" or self.climate in {"dry", "cold"}:
            concerns.add("dryness")
        if self.skin_type == "sensitive" or self.sensitivity_level == "high":
            concerns.update({"sensitivity", "redness"})
        if self.age_range in {"40s", "50s", "60+"}:
            concerns.add("fine_lines")
        if self.age_range in {"50s", "60+"}:
            concerns.add("wrinkles")
        return sorted(concerns)

    @property
    def effective_avoid_conditions(self) -> list[str]:
        conditions = set()
        if self.pregnancy:
            conditions.add("pregnancy")
        if self.skin_type == "sensitive" or self.sensitivity_level == "high":
            conditions.add("sensitivity")
        if self.skin_type == "acne_prone" or "acne" in self.concerns:
            conditions.add("acne")
        if "rosacea" in self.concerns:
            conditions.add("rosacea")
        if "dryness" in self.effective_concerns:
            conditions.add("dryness")
        return sorted(conditions)

    def as_dict(self) -> dict[str, Any]:
        return {
            "skin_type": self.skin_type,
            "concerns": self.concerns,
            "allergies": self.allergies,
            "age_range": self.age_range,
            "climate": self.climate,
            "budget": self.budget,
            "pregnancy": self.pregnancy,
            "sensitivity_level": self.sensitivity_level,
            "effective_concerns": self.effective_concerns,
            "effective_avoid_conditions": self.effective_avoid_conditions,
        }


class SkincareRecommender:
    def __init__(self, products: list[dict[str, Any]], ingredients_kb: dict[str, Any]):
        self.products = products
        self.kb = ingredients_kb
        self.ingredients = ingredients_kb["ingredients"]
        self.rules = ingredients_kb["rules"]
        self.routine_order = ingredients_kb["routine_order"]
        self.product_vectors = [self._product_vector(product) for product in products]

    @classmethod
    def from_files(cls, products_path: Path, ingredients_path: Path) -> "SkincareRecommender":
        with products_path.open() as products_file:
            products = json.load(products_file)
        with ingredients_path.open() as ingredients_file:
            ingredients = json.load(ingredients_file)
        return cls(products, ingredients)

    def recommend(self, profile: UserProfile) -> dict[str, Any]:
        scored = self.score_products(profile)
        am_routine = self._assemble_routine(scored, profile, "am")
        pm_routine = self._assemble_routine(scored, profile, "pm")
        return {
            "user_profile": profile.as_dict(),
            "am_routine": am_routine,
            "pm_routine": pm_routine,
            "am_validation": self._validate_routine(am_routine, "am"),
            "pm_validation": self._validate_routine(pm_routine, "pm"),
            "model_notes": [
                "Products are ranked with cosine similarity over concerns, skin type, ingredient functions, and key ingredients.",
                "The rule layer filters time-of-day restrictions, allergen matches, pregnancy/sensitivity contraindications, and active conflicts.",
                "This is an educational recommendation demo, not medical advice.",
            ],
        }

    def score_products(self, profile: UserProfile) -> list[dict[str, Any]]:
        user_vector = self._user_vector(profile)
        scored = []
        for product, product_vector in zip(self.products, self.product_vectors):
            cosine_score = _cosine_similarity(user_vector, product_vector)
            quality_score = _quality_score(product)
            similarity_score = (0.78 * cosine_score) + (0.22 * quality_score)
            scored.append(
                {
                    **_public_product(product),
                    "_all_ingredients": product.get("all_ingredients", []),
                    "similarity_score": round(similarity_score, 4),
                    "cosine_score": round(cosine_score, 4),
                    "quality_score": round(quality_score, 4),
                    "match_reasons": self._match_reasons(product, profile),
                }
            )
        scored.sort(key=lambda item: item["similarity_score"], reverse=True)
        return scored

    def _assemble_routine(
        self, scored_products: list[dict[str, Any]], profile: UserProfile, time_of_day: str
    ) -> list[dict[str, Any]]:
        routine = []
        selected_ingredients: set[str] = set()
        active_count = 0

        available_categories = {p["category"] for p in self.products}
        ordered_categories = [
            category
            for category in self.routine_order[time_of_day]
            if category in available_categories
        ]

        for category in ordered_categories:
            for product in scored_products:
                if product["category"] != category:
                    continue
                is_safe, reasons = self._is_safe_for_user(product, profile, time_of_day)
                if not is_safe:
                    continue
                if self._has_conflict(selected_ingredients, set(product["key_ingredients"])):
                    continue

                product_active_count = self._active_count(product["key_ingredients"])
                if active_count + product_active_count > self.rules["max_actives_per_routine"]:
                    continue

                routine.append({**_strip_internal(product), "safety_notes": reasons})
                selected_ingredients.update(product["key_ingredients"])
                active_count += product_active_count
                break

        return routine

    def _is_safe_for_user(
        self, product: dict[str, Any], profile: UserProfile, time_of_day: str
    ) -> tuple[bool, list[str]]:
        notes = []
        if product["time_of_day"] not in {"both", time_of_day}:
            return False, [f"Not recommended for {time_of_day.upper()} use"]

        if profile.budget != "any" and product["price_range"] != profile.budget:
            return False, [f"Outside {profile.budget} budget"]

        avoid_conditions = set(profile.effective_avoid_conditions)
        for condition in product.get("avoid_with_conditions", []):
            if condition in avoid_conditions:
                return False, [f"Avoid with {condition}"]

        all_ingredient_text = " ".join(
            product.get("_all_ingredients", product.get("all_ingredients", []))
        ).lower()
        key_ingredients = set(product.get("key_ingredients", []))
        for allergy in profile.allergies:
            terms = ALLERGY_TERMS.get(allergy, [allergy.replace("_", " ")])
            if any(term in all_ingredient_text for term in terms):
                return False, [f"Contains possible {allergy.replace('_', ' ')} trigger"]

        for ingredient in key_ingredients:
            contraindications = set(self.ingredients.get(ingredient, {}).get("contraindicated_for", []))
            blocked = contraindications & avoid_conditions
            if blocked:
                return False, [f"{ingredient} is contraindicated for {', '.join(sorted(blocked))}"]

        if product["category"] == "sunscreen":
            notes.append("Required final AM step")
        if product["time_of_day"] == "pm":
            notes.append("Best kept in the evening")
        return True, notes

    def _validate_routine(self, routine: list[dict[str, Any]], time_of_day: str) -> dict[str, Any]:
        categories = {product["category"] for product in routine}
        warnings = []
        synergies = []

        mandatory = set(self.rules.get("mandatory_both", []))
        if time_of_day == "am":
            mandatory.update(self.rules.get("mandatory_am", []))
        for category in sorted(mandatory):
            if category not in categories:
                warnings.append(f"No {category} found for this routine")

        ingredient_names = [ing for product in routine for ing in product["key_ingredients"]]
        ingredient_set = set(ingredient_names)
        for first, second in self.rules["avoid_combinations"]:
            if first in ingredient_set and second in ingredient_set:
                warnings.append(f"Avoid combining {first} with {second}")

        if {"hyaluronic acid", "ceramide"} & ingredient_set and {"glycerin", "squalane"} & ingredient_set:
            synergies.append("Hydrators and barrier-support ingredients work well together")
        if {"ascorbic acid", "tocopherol"} <= ingredient_set:
            synergies.append("Vitamin C and vitamin E can pair well as antioxidants")

        return {
            "is_valid": not warnings,
            "warnings": warnings,
            "synergies": synergies,
            "steps": len(routine),
        }

    def _user_vector(self, profile: UserProfile) -> dict[str, float]:
        vector: dict[str, float] = {}
        _add(vector, f"skin:{profile.skin_type}", 2.2)
        if profile.skin_type == "acne_prone":
            _add(vector, "skin:oily", 1.1)
        for concern in profile.effective_concerns:
            _add(vector, f"concern:{concern}", 3.0)
        if profile.climate in {"dry", "cold"}:
            _add(vector, "function:hydration", 1.2)
            _add(vector, "function:barrier_repair", 1.0)
        if profile.climate in {"humid", "tropical"}:
            _add(vector, "function:oil_control", 1.0)
        return vector

    def _product_vector(self, product: dict[str, Any]) -> dict[str, float]:
        vector: dict[str, float] = {}
        for skin_type in product["skin_types"]:
            _add(vector, f"skin:{skin_type}", 2.0)
        for concern in product["concerns_addressed"]:
            _add(vector, f"concern:{concern}", 3.0)
        for ingredient in product["key_ingredients"]:
            _add(vector, f"ingredient:{ingredient}", 0.75)
            for function in self.ingredients.get(ingredient, {}).get("function", []):
                _add(vector, f"function:{function}", 1.2)
        _add(vector, f"category:{product['category']}", 0.3)
        return vector

    def _has_conflict(self, selected: set[str], incoming: set[str]) -> bool:
        for first, second in self.rules["avoid_combinations"]:
            if (first in selected and second in incoming) or (second in selected and first in incoming):
                return True
        return False

    def _active_count(self, ingredients: list[str]) -> int:
        active_categories = {"active"}
        return sum(
            1
            for ingredient in ingredients
            if self.ingredients.get(ingredient, {}).get("category") in active_categories
        )

    def _match_reasons(self, product: dict[str, Any], profile: UserProfile) -> list[str]:
        reasons = []
        shared_concerns = sorted(set(product["concerns_addressed"]) & set(profile.effective_concerns))
        if shared_concerns:
            reasons.append(f"Targets {', '.join(shared_concerns[:3]).replace('_', ' ')}")
        if profile.skin_type in product["skin_types"] or (
            profile.skin_type == "acne_prone" and "oily" in product["skin_types"]
        ):
            reasons.append(f"Compatible with {profile.skin_type.replace('_', ' ')} skin")
        if product["key_ingredients"]:
            ingredients = [_ingredient_label(ingredient) for ingredient in product["key_ingredients"]]
            ingredients = [ingredient for ingredient in ingredients if ingredient][:3]
            if ingredients:
                reasons.append(f"Key ingredients: {', '.join(ingredients)}")
        return reasons[:3]


def options_payload() -> dict[str, Any]:
    return {
        "skin_types": sorted(VALID_SKIN_TYPES),
        "concerns": sorted(VALID_CONCERNS),
        "allergies": sorted(VALID_ALLERGIES),
        "age_ranges": ["teens", "20s", "30s", "40s", "50s", "60+"],
        "climates": sorted(VALID_CLIMATES),
        "budgets": ["any", "budget", "mid", "premium"],
        "sensitivity_levels": ["low", "normal", "high"],
    }


def _clean_values(values: list[str], allowed: set[str], label: str) -> list[str]:
    clean = []
    for value in values:
        if value not in allowed:
            raise ValueError(f"Invalid {label}: {value}")
        if value not in clean:
            clean.append(value)
    return clean


def _add(vector: dict[str, float], key: str, value: float) -> None:
    vector[key] = vector.get(key, 0.0) + value


def _cosine_similarity(first: dict[str, float], second: dict[str, float]) -> float:
    shared = set(first) & set(second)
    numerator = sum(first[key] * second[key] for key in shared)
    first_norm = math.sqrt(sum(value * value for value in first.values()))
    second_norm = math.sqrt(sum(value * value for value in second.values()))
    if not first_norm or not second_norm:
        return 0.0
    return numerator / (first_norm * second_norm)


def _quality_score(product: dict[str, Any]) -> float:
    rank = product.get("rank") or 0
    price_bonus = {"budget": 0.05, "mid": 0.03, "premium": 0.0}.get(product.get("price_range"), 0.0)
    return max(0.0, min(1.0, (float(rank) / 5.0) + price_bonus))


def _public_product(product: dict[str, Any]) -> dict[str, Any]:
    visible_keys = [
        "id",
        "name",
        "brand",
        "category",
        "time_of_day",
        "skin_types",
        "concerns_addressed",
        "key_ingredients",
        "price",
        "price_range",
        "rank",
        "texture",
        "avoid_with_conditions",
        "description",
    ]
    return {key: product.get(key) for key in visible_keys}


def _strip_internal(product: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in product.items() if not key.startswith("_")}


def _ingredient_label(ingredient: str) -> str:
    if not ingredient:
        return ""
    if ":" in ingredient or len(ingredient) > 44:
        return ""
    return ingredient
