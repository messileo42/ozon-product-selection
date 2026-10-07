---
name: ozon-product-selection
description: Run a guided, one-question-at-a-time Ozon product-selection workflow for the Russian market using public Ozon data and 1688 supplier information. Use when the user wants to discover, compare, shortlist, or source products for Ozon. Produces both a chat summary and an Excel workbook, then performs Russian keyword and listing-copy analysis only for user-selected finalists. Excludes seller-account APIs, product upload, pricing changes, and inventory actions.
---

# Ozon Product Selection

Guide the user from selection criteria to an evidence-backed shortlist. Ask exactly one question per assistant turn. Do not begin market research until the intake summary has been confirmed.

## Fixed scope

- Sales market: Russia on Ozon.
- Sources: public Ozon market information and 1688 supplier information only.
- Supplier platform: 1688.
- No seller credentials, private analytics, or seller-account API access.
- Do not upload products, modify listings, set prices, contact suppliers, place orders, or change inventory.
- Do not impose a profit target or reject a product based on estimated profit. Display the observed Ozon price and 1688 purchase price instead.
- Size and weight are decision data, not automatic exclusion rules. Show them clearly and place unusually large or heavy products in a separate review group for the user.

## Phase 1: guided intake

Ask the following questions in order, one per turn. Accept free-form answers. Do not repeat a question already answered in the current conversation.

1. **Category:** What product category or categories should be researched? Also accept excluded subcategories in the same answer.
2. **Selection dimensions:** Ask the user to choose and rank the important dimensions. Offer: market demand, low competition, Ozon selling price, 1688 purchase price, size/weight, seasonality, repeat purchase, low return risk, differentiation, and Russian keyword/search opportunity. Allow custom dimensions.
3. **Price ranges:** Ask for both the target Ozon selling-price range and 1688 unit-purchase-price range. Allow “no limit” for either.
4. **Selling period:** Ask whether the products are for immediate launch, a specified month/season, or year-round sales.
5. **Candidate count:** Ask how many candidates the user wants in this run.

After the last answer, summarize the full brief, including the fixed scope, and ask one confirmation question. Begin research only after an affirmative answer. If the user changes a condition, update the summary and confirm again.

## Phase 2: research and screening

Use current web research because demand, prices, competition, supplier offers, and marketplace rules change frequently.

1. Research distinct product directions on public Ozon pages and current external sources that directly support Russian demand.
2. Use public proxies when Ozon does not expose real query rate, search volume, CTR, conversion, or orders. Useful proxies include keyword suggestions, search-result density, title-word frequency, current price distribution, bestseller/category position, review recency or velocity, seller concentration, and external trend data.
3. Label every metric as a fact, proxy, estimate, or forecast. Record its source URL, observation date, and covered period. Never present a proxy as private Ozon data.
4. Match promising directions to specific 1688 offers when reliable offers are available. It is acceptable to return a product direction without a specific offer, or a specific offer when that is the stronger result.
5. For 1688 offers, capture the exact variant, current price tier, MOQ, available weight, dimensions, supplier, and offer URL. Never substitute carton measurements for unit measurements. Mark unavailable fields as unknown.
6. Automatically exclude products that are powered or battery-operated, liquids, magnetic, fragile, likely to infringe brands or copyrighted designs, or likely to require unclear certification. List excluded ideas and the reason; do not include them in the requested candidate count.
7. Do not automatically exclude large or heavy products. Separate them into a clearly labeled “size/weight review” section so the user can decide.
8. Rank candidates according to the user’s chosen dimension order. Explain the most important evidence behind each rank; do not create an unrequested universal score formula.
9. If evidence is too weak to fill the requested count, return fewer candidates and explain why instead of padding the list.

## Phase 3: initial delivery and finalist selection

Return the initial results in both places:

- A readable chat table.
- An `.xlsx` workbook created with the spreadsheet skill and visually verified before delivery.

Use these workbook sheets:

- `候选池`: ranked candidates.
- `尺寸重量复核`: large or heavy candidates requiring user judgment.
- `自动排除`: excluded ideas and reasons.
- `来源与方法`: sources, dates, metric definitions, proxies, assumptions, and limitations.

For each candidate include, when available:

- Rank and product direction.
- Specific 1688 product and URL.
- Ozon demand evidence.
- Russian search/keyword opportunity summary.
- Competition assessment and basis.
- Observed Ozon selling-price range.
- 1688 unit purchase price and MOQ.
- Unit or packed weight and dimensions.
- Trend and seasonality.
- Main risk.
- Whether each important value is verified, proxied, estimated, or unknown.

Do not generate final titles or promotional copy yet. After delivering the candidate pool, ask one question: which candidate numbers should enter the final analysis?

## Phase 4: final keyword and copy analysis

Run this phase only for candidates explicitly selected by the user.

For each finalist:

1. Perform deeper Russian search-intent analysis using public evidence and clearly labeled proxies.
2. Identify the primary Russian keyword, supporting keywords, long-tail phrases, customer intent, and important synonyms. Do not claim a real query rate when none is publicly available.
3. Produce a Russian product title designed for relevance and readability, not keyword stuffing.
4. Produce a concise Russian promotional phrase.
5. Provide Chinese translations for the title, promotional phrase, and keyword set.
6. Explain which terms are evidence-backed, which are inferred, and what should be tested later.

Update both the chat result and the same Excel workbook. Add or refresh a `最终关键词与文案` sheet containing:

- Candidate identifier.
- Russian title and Chinese translation.
- Russian promotional phrase and Chinese translation.
- Primary, supporting, and long-tail Russian keywords.
- Search-intent explanation.
- Evidence/proxy sources and observation dates.
- Uncertainty and recommended test.

## Quality rules

- Use one row per genuinely distinct product proposition, not superficial color or size variants.
- Prefer original Ozon and 1688 pages; third-party indexes are leads, not verified supplier evidence.
- Keep facts, proxies, estimates, and forecasts visibly separate in chat and Excel.
- Do not fabricate demand, search rate, sales, orders, CTR, conversion, reviews, prices, weights, dimensions, or links.
- Treat Russian copy as a final-stage deliverable, never as evidence that a product has demand.
- Stop after the final chat and workbook are delivered. Any listing or account work requires a separate request and workflow.
