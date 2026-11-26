# Judge rubric: local buyer suggestions

You score each pending suggestion from its photo (contact sheet), Arabic name, price, product type and notes.
Score each item on its own merits. Don't look up how it did later, and don't try to balance the scores.

Context: Fedshi resellers sell to Iraqi cash-on-delivery buyers through short video ads. A "winner" passes the
ghost test (resellers' ad campaigns): about 31% do. Sourcing prices are in IQD (about 1,300 IQD = $1); resellers
sell at about 1.5–3× the sourcing price.

## Scores (1–5)
Only the first three go into the score (v1). The other three are recorded to test new weights later.

| Key | Meaning | Weight in v1 |
|---|---|---|
| `novelty` | How rare the item is in ordinary Iraqi shops and pages. 5 = rarely seen, 3 = a few pages sell it, 1 = in every shop. Be strict: generic gadgets every phone, car or home shop sells score 1–2. | 50% |
| `wow` | Wow factor or a clear problem solved: something that stops the scroll. | 25% |
| `video` | How easy it is to make a convincing short video ad: visible demo, before/after, mechanism. | 25% |
| `mass` | Mass-market appeal for Iraqi households. | recorded |
| `look` | Perceived value from the photo: 1 = looks like a cheap 5k item, 5 = clearly worth paying for. | recorded |
| `season` | Fit for the current season in Iraq: summer heat and dust, cold Dec–Feb, Ramadan and Eid, school. | recorded |

Backtest notes (240 suggestions, Sep–Nov 2026):
- Novelty matched Ahmed's approvals best (AUC 0.69).
- Wow and video predicted winners (0.59–0.62).
- Mass, season and look did not, so don't let them pull the other scores.
- Cheap impulse items with a clear demo often win, so a low price or simple build is no reason to score low.

## Also give
- `why`: one short English reason (it is shown to the reviewer).
- `angles`: 1–3 selling-angle tags for testers, from `wow, problem_solver, mass_appeal, gift, seasonal, video_friendly,
  car, kitchen, home, health, baby, beauty_device, tools, outdoor`.
- `x` (optional, a note only, never an automatic rejection): `low_value`, `kids_toy`, `consumable`, `sized`, `cosmetic`,
  `bulky`, `fragile`, `not_product`.

## Answer file
One per sheet, `data/judge/answer_NN.json`:
```json
{"SUG-12345": {"novelty": 4, "wow": 3, "video": 4, "mass": 3, "look": 3, "season": 3,
               "why": "Rare car organiser with an easy before/after", "angles": ["car", "problem_solver"], "x": null}}
```
Every ticket on the sheet needs an answer.
