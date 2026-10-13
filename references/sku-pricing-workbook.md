# SKU-level sourcing and pricing workbook

Read this reference whenever Phase 3 creates the Ozon listing-reference workbook. The main `SKILL.md` defines product-selection decisions; this reference defines variant expansion, source extraction, cost tiers, freight, suggested pricing, and final-file cleanup.

## Required source workbooks

Before pricing, locate the current `.xlsx` files under the active project's `inputs/` directory that provide:

1. the Ozon cross-border pricing/freight calculator; and
2. the GUOO product tariff calculator.

Treat both files as read-only sources. Use the spreadsheet skill to inspect their current values, formulas, units, route names, weight/value bands, size limits, chargeable-weight logic, commissions, exchange rate, per-order fees, and percentage fees. Do not rely on rates remembered from a previous run or copy formulas from an older output.

Use the route specified by the user. If none is specified, use the route used by the current cross-border pricing calculator, normally the applicable Ozon realFBS economy route, and record that assumption in `定价依据`. If the two source workbooks disagree, do not silently choose the cheaper result. Use the higher applicable freight for the suggested-price floor or leave pricing unresolved when the conflict changes channel eligibility.

## SKU-row expansion

The listing-reference workbook is variant-grain data, not product-grain data.

- One sellable 1688 specification or variant combination equals one row.
- A product with `N` intended sellable specifications produces `N` rows. Repeated product names and product-detail URLs are expected.
- Expand the exact variants intended for Ozon listing. Do not create rows for variants that violate the selected product proposition, prohibited substitutions, safety rules, or intellectual-property rules.
- Preserve the supplier's variant order where practical so the workbook can be checked against the detail page.

For each row, open the exact authenticated 1688 product-detail page. A search-results URL is not acceptable as a product-detail URL. Prefer the canonical offer URL or a direct mobile detail URL containing the offer ID. If no exact product-detail page can be verified, leave the link blank and do not present search-card data as verified SKU data.

## Main sheet schema

The main sheet is `Ozon上品参考` and has exactly these columns in this order:

1. `sku`
2. `自定义货号`
3. `重量（g）`
4. `长度（mm）`
5. `宽度（mm）`
6. `高度（mm）`
7. `商品详情页链接`
8. `成本价`
9. `建议售价`

Field rules:

- `sku`: use the exact SKU/specification identifier shown by 1688 or reliably bound to that exact variant. Do not use the offer ID as a SKU and do not invent an SKU. Leave blank if the exact variant identifier cannot be captured.
- `自定义货号`: uppercase pinyin initials of the Chinese product name, one to four letters, followed by a unique four-digit sequence. Remove brand names before forming the prefix. Sort by product decision rank and supplier variant order, then assign `0001`, `0002`, and so on. Each row must be unique. Example format: `BZ0001`.
- `重量（g）` and dimensions: use variant-specific unit shipping/packed data from the exact 1688 detail page when available. Convert kilograms to grams and centimeters to millimeters. Do not substitute carton data, another variant's data, category estimates, or visual guesses. Leave missing values blank.
- `商品详情页链接`: store the verified exact 1688 detail URL as a hyperlink. The same offer URL may repeat across its variants.
- Numeric measurement and suggested-price cells must be numeric, not numbers embedded in text. Keep `sku` and `自定义货号` as text.

## Cost-price field

Build `成本价` from the exact variant's authenticated 1688 detail page, not a search card.

- Capture MOQ, every visible quantity-price tier, currency, and whether the value is per piece, set, pair, pack, or another unit.
- Express the cell as concise structured text, for example: `MOQ 2件；2–49件 ¥12.80/件；50–199件 ¥11.90/件；≥200件 ¥10.80/件`.
- When supplier domestic freight, packaging, customization, or mandatory accessories are visible and attributable per order or per unit, include them in the detailed pricing build. Otherwise mark them unknown; never assume they are free.
- Calculate total procurement cost for at least the executable first-test quantity and each genuine supplier price tier. Do not fabricate a discount curve when only one price is visible.
- Use the unit price for the intended first-test quantity when calculating the main suggested price. Do not price the first test using an unreachable large-order tier.

## Freight and chargeable weight

Use the current formulas and limits from the two input workbooks.

1. Convert the captured weight and dimensions to the units required by the source workbook.
2. Determine the applicable product/parcel group from chargeable weight and proposed Ozon value.
3. Apply the current actual-versus-volumetric-weight rule, dimensional divisor, maximum side, sum-of-sides, weight, and value restrictions from the source workbooks.
4. Apply the selected route's current per-kilogram and per-order fees.
5. Where proposed price affects the parcel group, iterate price, group, chargeable weight, and freight until the applicable group is stable.
6. If weight or any required dimension is unavailable, leave `建议售价` blank. Do not disguise missing freight inputs with a category-average estimate.

## Suggested-price model

Create a second sheet named `定价依据` in the listing-reference workbook. It may contain additional calculation columns; the nine-column main sheet must remain unchanged.

For every custom item number, show:

- exact 1688 variant and procurement tier used;
- item cost and known domestic/packaging cost in CNY;
- actual weight, volumetric weight, chargeable weight, logistics group, route, and freight in CNY;
- label/per-order fee, exchange rate, Ozon category commission, other percentage fees, and their sources;
- break-even price, conservative price floor, observed comparable Ozon price band, recommended price, and pricing status;
- assumptions, missing inputs, observation date, and source workbook/detail-page references.

Calculate from known inputs:

`known unit cost = item cost + known domestic/packaging cost + international freight + fixed per-order/label fees`

`break-even sale price = known unit cost / (1 - commission rate - other percentage fees)`

For a conservative floor, include an explicit return/risk reserve and target contribution buffer. If the user does not provide them, use these editable professional defaults:

- return/risk reserve: 3% for simple low-return goods, 5% for ordinary goods, and 8%–12% for fit-sensitive, installation-sensitive, fragile, or high-return goods;
- target contribution buffer after known variable costs: 15%.

`conservative floor = known unit cost / (1 - commission rate - other percentage fees - return/risk reserve - target contribution buffer)`

Use the current Ozon category commission when it can be verified. Otherwise use the calculator's current documented assumption; if neither is available, use a clearly labeled conservative estimate rather than leaving the formula silently optimistic.

Choose the recommended RUB price as follows:

1. Base it on the first executable purchase tier, not the cheapest scale tier.
2. It must not fall below the conservative price floor.
3. It must fit a defensible position in the current comparable Ozon price distribution.
4. Round upward, not downward, using a practical marketplace increment.
5. If the conservative floor is above the defensible market ceiling, leave `建议售价` blank, mark the item `暂停：成本与市场价不匹配` in `定价依据`, and downgrade or hold the product-selection decision.

Show the effect of MOQ, middle, and scale purchase tiers in `定价依据`. Scale discounts improve margin; they do not justify lowering the launch price before demand is proven.

No suggested price is a profit guarantee. Unknown advertising, storage, return, tax, domestic freight, packaging, or promotion costs must remain visible as missing inputs or assumptions.

## Workbook construction and cleanup

- Create both final workbooks with the spreadsheet skill and visually verify every sheet.
- Use a task-specific temporary directory for builders, previews, extracts, inspect files, JSON, and CSV intermediates.
- After both final `.xlsx` files pass structural, formula-error, saved-file, and visual checks, delete only the intermediates created for the current run.
- Do not delete source files in `inputs/`, unrelated prior outputs, user files, or the two verified final workbooks.
- The final output directory for the run must contain exactly the two requested `.xlsx` deliverables.
