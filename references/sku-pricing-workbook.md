# SKU-level sourcing and pricing workbook

Read this reference whenever Phase 3 creates the Ozon listing-reference workbook. The main `SKILL.md` defines product-selection decisions; this reference defines variant expansion, source extraction, cost tiers, freight, suggested pricing, and final-file cleanup.

## Required source workbooks

Before pricing, locate the current `.xlsx` files under the active project's `inputs/` directory that provide:

1. the Ozon cross-border pricing/freight calculator; and
2. the GUOO product tariff calculator.

Treat both files as read-only sources. Use the spreadsheet skill to inspect their current values, formulas, units, route names, weight/value bands, size limits, chargeable-weight logic, commissions, exchange rate, per-order fees, and percentage fees. Do not rely on rates remembered from a previous run or copy formulas from an older output.

Use the route specified by the user. If none is specified, use the route used by the current cross-border pricing calculator, normally the applicable Ozon realFBS economy route, and record that assumption in `定价依据`. If the two source workbooks disagree, do not silently choose the cheaper result. Use the higher applicable freight for the suggested-price floor or leave pricing unresolved when the conflict changes channel eligibility.

## SKU-row expansion

The listing-reference workbook is variant-grain data, not product-grain data. In this workbook, `sku` is the human-readable sellable attribute key used to distinguish rows; it does not require a hidden 1688 numeric SKU ID.

### Product-adaptive attribute discovery

Do not start with a fixed category schema. For each offer, infer its structure from the authenticated page and classify what is shown:

- **Sellable axes:** choices that define an orderable variant or change price, inventory, supplier code, MOQ, included contents, or fulfillment. Depending on the product these may be color, size, model, capacity, quantity, set composition, material/finish, compatibility, connector, pattern, scent, or another supplier-defined axis. This list is illustrative, not exhaustive.
- **Variant-bound descriptors:** measurements or explanations tied to a selected option, such as fit ranges, capacity, diameter, usable length, compatible model, or included accessory. Preserve them in the SKU text when they are needed to distinguish or correctly understand the option.
- **Offer-level attributes:** material, process, origin, brand status, customization, and other facts shared by all variants. Record them as supporting evidence; do not create fake SKU axes from them.
- **Logistics measurements:** single-unit packed weight and packed length/width/height. Keep these separate from product dimensions and functional specifications.
- **Marketing content:** claims, scenes, and decorative text that do not define a purchasable option. Do not turn them into SKU data.

Observe what changes as options are selected. A visible option group is a sellable axis only if it participates in an orderable combination. One product may have no variant axes; another may have several. Apply the page's structure rather than forcing all products into the same extraction recipe.

- One sellable 1688 specification or variant combination equals one row.
- A product with `N` intended sellable specifications produces `N` rows. Repeated product names and product-detail URLs are expected.
- Read every actual sellable axis from the authenticated offer and preserve the supplier's axis order and exact option wording.
- When axes are independent, create their Cartesian product. When selecting one option disables, removes, sells out, changes, or constrains another option, include only the combinations the page actually permits the buyer to select and purchase. Never manufacture a theoretical combination without testing availability.
- Build the `sku` cell by joining the selected option labels with a backslash. Keep enough supplier wording to distinguish the variant correctly. `粉色\XS胸30背20 约1-2斤左右` is one illustrative result; other products may use combinations such as capacity and pack count, model and compatibility, finish and dimensions, or a completely different schema.
- For an offer with no sellable axis, create one row using the supplier's concise product/model/specification label as the SKU display key. Do not invent a color, size, or other attribute merely to make the cell look structured.
- Expand the exact variants intended for Ozon listing. Do not create rows for variants that violate the selected product proposition, prohibited substitutions, safety rules, or intellectual-property rules.
- Preserve the supplier's variant order where practical so the workbook can be checked against the detail page.
- Creating one placeholder row per product is not an acceptable substitute for variant expansion. If authenticated access is blocked, pause and ask the user to restore the logged-in session instead of delivering the placeholder as a completed listing-reference workbook.

For each row, open the exact authenticated 1688 product-detail page. A search-results URL is not acceptable as a product-detail URL. Prefer the canonical offer URL or a direct mobile detail URL containing the offer ID. If no exact product-detail page can be verified, leave the link blank and do not present search-card data as verified SKU data.

## Image-based specification extraction

1688 suppliers often publish SKU identifiers, weight, dimensions, and packaging details only as pixels inside carousel images, long detail images, specification charts, or packaging diagrams. Absence from selectable page text is not evidence that the data is unavailable. Complete this workflow for every listing-ready A or B offer before leaving those fields blank.

1. After reading selectable text and the `商品属性`/product-attributes area, open the exact authenticated offer and enumerate its actual intended sellable variant combinations. Record every relevant axis and variant-bound descriptor in supplier order. Images are a fallback or corroborating source, not a reason to skip selectable attributes.
2. Inspect all relevant image surfaces: carousel images, variant thumbnails, the full detail-description image stream, specification/parameter charts, packaging diagrams, and any image that becomes visible after selecting a variant. Scroll through lazy-loaded content before deciding that the image set is complete.
3. Open a relevant image at its largest available resolution. Prefer the original image or a lossless capture of the rendered image. If a long image is unreadable at page scale, zoom or capture overlapping readable regions rather than performing OCR on a blurred full-page screenshot.
4. Extract the raw Chinese label, value, and unit for possible SKU/model/item number, net weight, gross or packed weight, product size, single-unit package size, pack count, and outer-carton size. OCR is a discovery pass, not the final authority.
5. Re-read the original image visually and compare every character and decimal used in the workbook. Re-capture and retry when OCR and the visible image disagree. Never average conflicting readings or silently choose the value that produces cheaper freight.
6. Bind each extracted record to the exact variant using an explicit row label, header, color/size/model name, diagram caption, or variant-specific image state. If the image presents a table, map each row or column separately. Do not assign a generic image value to every variant unless the page explicitly states that the specification is shared.
7. Classify measurement meaning before normalization:
   - `单件包装/含包装/毛重` is eligible for the main sheet and freight calculation.
   - `产品尺寸/净重` may be recorded as supporting evidence but must not be treated as packed logistics data.
   - `装箱数/整箱/外箱/箱规/箱重` is carton-level data and must not be copied into the main sheet's unit fields.
   - Multi-pack data must be converted to a single sellable unit only when the image explicitly provides enough information and the sellable unit definition is unambiguous; otherwise leave unresolved.
8. Preserve an audit record in `定价依据`: source type (`页面文字`, `详情图`, or `规格图`), exact variant label, raw recognized text, normalized value, unit conversion, image position or description, detail-page URL, observation date, and extraction confidence (`高`, `中`, or `低`). Do not put temporary local image paths in the final workbook.

Confidence rules:

- `高`: clear original image, unambiguous label/unit, and explicit variant mapping; OCR or transcription visually confirmed.
- `中`: readable value and unit but the image applies to a product family or the variant mapping needs a stated interpretation. Keep the assumption visible and do not use it for freight when it could materially change the group or price.
- `低`: blurred/cropped image, missing unit, ambiguous decimal, conflicting charts, or uncertain variant mapping. Treat the field as unresolved rather than numeric.

If the page contains conflicting image and text values, prefer neither automatically. Record both, identify their meanings and update dates when visible, and use the safer higher packed weight or larger packed dimensions only when both clearly describe the same sellable unit. Otherwise leave freight pricing unresolved and flag supplier confirmation as the next action.

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

- `sku`: join the exact visible labels of the product's actual selected variant axes with `\`. This is a deterministic display key, not an invented product specification. Any example in this reference is illustrative only. If 1688 also exposes a separate internal SKU code or supplier model, record it in `定价依据`; do not leave the main `sku` blank merely because that code is absent.
- `自定义货号`: uppercase pinyin initials of the Chinese product name, one to four letters, followed by a unique four-digit sequence. Remove brand names before forming the prefix. Sort by product decision rank and supplier variant order, then assign `0001`, `0002`, and so on. Each row must be unique. Example format: `BZ0001`.
- `重量（g）` and dimensions: use variant-specific single-unit shipping/packed data from selectable text or a visually verified detail-page image. Convert kilograms to grams and centimeters to millimeters while retaining raw values in `定价依据`. Product-specific measurements—such as fit measurements, diameter, usable length, capacity, compatible-device size, or recommended user/pet range—are not automatically package length/width/height. Keep variant-bound descriptors in `sku` or supporting evidence and do not force them into logistics columns. Do not substitute product-only dimensions, net weight, carton data, another variant's data, category estimates, or a visual size guess. Blank logistics dimensions are acceptable after complete inspection and do not block row creation or cost extraction.
- `商品详情页链接`: store the verified exact 1688 detail URL as a hyperlink. The same offer URL may repeat across its variants.
- Numeric measurement and suggested-price cells must be numeric, not numbers embedded in text. Keep `sku` and `自定义货号` as text.

## Cost-price field

Build `成本价` from the exact variant's authenticated 1688 detail page, not a search card.

- Cost extraction is independent of freight completeness. Never leave `成本价` blank merely because weight, dimensions, a freight calculator, commission, or exchange rate is missing.
- Select each valid attribute combination and observe whether its price, MOQ, or stock state changes. Use the combination-specific price when it changes; otherwise repeat the verified offer-level price tiers across the applicable rows.
- Capture MOQ, every visible quantity-price tier, currency, and whether the value is per piece, set, pair, pack, or another unit.
- Express the cell as concise structured text, for example: `MOQ 2件；2–49件 ¥12.80/件；50–199件 ¥11.90/件；≥200件 ¥10.80/件`.
- If 1688 exposes only an offer price range after all selectable combinations are checked, record the visible range and MOQ rather than leaving the cell blank. Use the upper end for provisional pricing and mark `单规格价待确认` in `定价依据`.
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
6. Missing package dimensions alone do not force `建议售价` to be blank. Apply the conservative proxy hierarchy below and label the result `暂估`.

### Conservative logistics proxy hierarchy

Use exact freight inputs whenever possible. If they are incomplete, attempt these options in order and stop at the first defensible method:

1. If exact single-unit packed weight is known but dimensions are missing, decide whether actual-weight pricing is defensible from the product's compressibility, rigidity, shape, packaging mode, and route rules. When it is, calculate actual-weight freight and add a separately disclosed volumetric/packing uncertainty reserve derived from verified comparable SKUs in the current run when possible. When it is not, continue to the next proxy or pause. Do not apply an apparel-specific shortcut to unrelated goods.
2. If exact weight is missing, use chargeable-weight evidence from materially comparable verified SKUs in the current run: same product class, material/rigidity, packaging mode, pack count, and approximate physical scale. With four or more comparables use the 75th percentile; with fewer than four use the maximum. List the custom item numbers used as the proxy set. Choose comparison criteria that fit the product rather than reusing a fixed category template.
3. If the supplier provides carton weight, carton dimensions, and units per carton, derive a per-unit weight or volume only when the allocation is mathematically unambiguous and packaging arrangement is credible. Label it as a derived proxy, not a supplier-stated unit measurement.
4. If none of these methods is supportable, leave `建议售价` blank and mark `暂停：缺少可辩护的物流代理`. Do not use an unsupported generic category average.

A proxy-backed price remains a launch estimate. It must be recalculated after sampling or supplier confirmation of packed weight and dimensions. Missing dimensions can remain blank in the main sheet even when a documented proxy supports a provisional suggested price.

## Suggested-price model

Create a second sheet named `定价依据` in the listing-reference workbook. It may contain additional calculation columns; the nine-column main sheet must remain unchanged.

For every custom item number, show:

- exact 1688 variant and procurement tier used;
- item cost and known domestic/packaging cost in CNY;
- actual weight, volumetric weight, chargeable weight, logistics group, route, and freight in CNY;
- image-extraction audit fields for image-derived values: source type, raw recognized text, image position/description, normalized value, variant mapping, and confidence;
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

Set `定价状态` to one of:

- `正式`: exact variant cost and sufficient packed logistics inputs were used.
- `暂估：物流代理`: exact or conservatively bounded variant cost was used with the documented proxy hierarchy. Populate the numeric `建议售价`, expose the proxy and reserve, and require recalculation after sampling.
- `暂停`: no executable supplier cost, no defensible logistics basis, or the conservative floor exceeds the market ceiling. State the exact blocker.

Do not withhold all suggested prices merely because some variants lack package dimensions. Price each row independently from the best evidence available, and use the same suggested price across variants only when their cost, logistics basis, and market positioning are genuinely the same.

Show the effect of MOQ, middle, and scale purchase tiers in `定价依据`. Scale discounts improve margin; they do not justify lowering the launch price before demand is proven.

No suggested price is a profit guarantee. Unknown advertising, storage, return, tax, domestic freight, packaging, or promotion costs must remain visible as missing inputs or assumptions.

## Workbook construction and cleanup

- Create both final workbooks with the spreadsheet skill and visually verify every sheet.
- Use a task-specific temporary directory for builders, previews, extracts, inspect files, JSON, and CSV intermediates.
- Store downloaded detail images, screenshots, OCR crops, and recognition output only in that task-specific temporary directory. They are working evidence, not additional final deliverables.
- After both final `.xlsx` files pass structural, formula-error, saved-file, and visual checks, delete only the intermediates created for the current run.
- Do not delete source files in `inputs/`, unrelated prior outputs, user files, or the two verified final workbooks.
- The final output directory for the run must contain exactly the two requested `.xlsx` deliverables.
