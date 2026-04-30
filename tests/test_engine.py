import unittest
from pathlib import Path

from skincare_engine import SkincareRecommender, UserProfile


ROOT = Path(__file__).resolve().parents[1]


class RecommenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recommender = SkincareRecommender.from_files(
            ROOT / "products_processed.json",
            ROOT / "ingredients_kb.json",
        )

    def test_effective_profile_infers_concerns(self):
        profile = UserProfile(skin_type="oily", concerns=["acne"], age_range="50s")

        self.assertIn("excess_oil", profile.effective_concerns)
        self.assertIn("fine_lines", profile.effective_concerns)
        self.assertIn("wrinkles", profile.effective_concerns)

    def test_recommendation_has_am_and_pm_steps(self):
        profile = UserProfile(
            skin_type="combination",
            concerns=["acne", "dullness", "fine_lines"],
            budget="any",
        )

        result = self.recommender.recommend(profile)

        self.assertGreaterEqual(len(result["am_routine"]), 3)
        self.assertGreaterEqual(len(result["pm_routine"]), 3)
        self.assertTrue(any(p["category"] == "sunscreen" for p in result["am_routine"]))

    def test_pregnancy_profile_filters_retinol(self):
        profile = UserProfile(
            skin_type="normal",
            concerns=["fine_lines"],
            pregnancy=True,
        )

        result = self.recommender.recommend(profile)
        ingredients = {
            ingredient
            for routine_name in ["am_routine", "pm_routine"]
            for product in result[routine_name]
            for ingredient in product["key_ingredients"]
        }

        self.assertNotIn("retinol", ingredients)

    def test_allergy_filter_uses_full_ingredient_list(self):
        profile = UserProfile(
            skin_type="combination",
            concerns=["dullness", "fine_lines"],
            allergies=["fragrance"],
        )

        result = self.recommender.recommend(profile)
        products_by_id = {product["id"]: product for product in self.recommender.products}
        ingredient_text = " ".join(
            ingredient.lower()
            for routine_name in ["am_routine", "pm_routine"]
            for product in result[routine_name]
            for ingredient in products_by_id[product["id"]].get("all_ingredients", [])
        )

        self.assertNotIn("fragrance", ingredient_text)


if __name__ == "__main__":
    unittest.main()
