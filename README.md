# SkinSync Skincare Recommender

SkinSync is a full-stack demo for a personalized skincare routine recommender. It combines a content-based ML scoring layer with a dermatology-inspired rule engine so users can generate AM and PM routines from their skin type, concerns, budget, allergies, climate, age range, and pregnancy-safe preferences.

## What is in the demo

- `skincare_engine.py` loads the processed product catalog and ingredient knowledge base, scores products with cosine similarity, applies safety filters, and assembles AM/PM routines.
- `backend.py` serves a small JSON API and the frontend using only the Python standard library.
- `static/` contains the live demo UI.
- `products_processed.json` and `ingredients_kb.json` are the deployable model artifacts exported from the Colab notebook.
- `tests/` has basic regression tests for profile inference, routine generation, and pregnancy-safe filtering.

## Run locally

```bash
python3 backend.py
```

Then open:

```text
http://127.0.0.1:8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

Run tests:

```bash
python3 -m unittest discover -s tests
```

## API

`GET /api/options`

Returns valid skin types, concerns, allergies, budgets, climates, and sensitivity levels for the UI.

`POST /api/recommend`

Example payload:

```json
{
  "skin_type": "combination",
  "concerns": ["acne", "dullness", "fine_lines"],
  "allergies": ["fragrance"],
  "age_range": "30s",
  "climate": "temperate",
  "budget": "any",
  "pregnancy": false,
  "sensitivity_level": "normal"
}
```

The response includes `user_profile`, `am_routine`, `pm_routine`, validation warnings, synergies, match scores, and match reasons.

## Deploy for a live demo

The app has no third-party runtime dependencies, so deployment is intentionally simple.

### Render

1. Push this repo to GitHub.
2. Create a new Render Web Service from the repo.
3. Use Python as the runtime.
4. Build command: leave blank or use `pip install -r requirements.txt`.
5. Start command: `HOST=0.0.0.0 python backend.py`.

Render will provide `PORT`; `backend.py` reads it automatically.

### Railway

1. Create a Railway project from the GitHub repo.
2. Set the start command to `HOST=0.0.0.0 python backend.py`.
3. Deploy.

## Suggestions for the project

### Model improvements

- Add an evaluation set: create 20 to 50 realistic user profiles and expected product categories, then measure whether the recommender picks safe, sensible routines.
- Separate score components in the UI: show concern match, skin-type match, quality/rating, and rule penalties so judges can understand the ML decision.
- Add explainability: include why a product was filtered out, not just why selected products were chosen.
- Improve allergy matching: the current deployed version checks broad ingredient terms, but a production system should normalize every ingredient in `all_ingredients`.
- Add routine diversity: prevent one brand from dominating a routine unless it is clearly the best option.
- Add SPF and active-use education: warn users when PM actives make sunscreen especially important the next morning.

### Data improvements

- Refresh the catalog with current availability, product URLs, and image URLs before presenting publicly.
- Add patch-test and medical disclaimer language in the UI.
- Add ingredient concentration when available. Ingredient order helps, but exact percentages would improve safety and scoring.
- Track product format, such as gel, cream, balm, oil, and lotion, because texture matters a lot for oily, dry, and acne-prone users.

### Demo improvements

- Add a side-by-side comparison mode for two profiles.
- Add a "why not" panel that shows filtered products and safety reasons.
- Save/share routines with a generated link or downloadable summary.
- Turn notebook export into a repeatable script so the deployed JSON artifacts can be regenerated after data changes.
