# WorkBuddy extraction bridge

Read this reference only when WorkBuddy is available and the product-selection workflow is ready to inspect exact 1688 detail offers. The bridge delegates page extraction, not product judgment or pricing.

## Runtime contract

Use `scripts/workbuddy_bridge.py` with a task-specific runtime directory outside the final output directory. The default local convention is `<active-project>/workbuddy-bridge/`.

```powershell
& scripts/workbuddy_bridge.ps1 init --runtime-dir D:\CodexProject\Ozon\workbuddy-bridge
& scripts/workbuddy_bridge.ps1 enqueue --runtime-dir D:\CodexProject\Ozon\workbuddy-bridge --candidate-id A01 --url https://detail.1688.com/offer/123456789.html --test-quantity 20 --warehouse "中国集货仓"
& scripts/workbuddy_bridge.ps1 attach-browser-evidence --runtime-dir D:\CodexProject\Ozon\workbuddy-bridge --job A01-123456789 --evidence D:\CodexProject\Ozon\workbuddy-bridge\browser-capture.json
& scripts/workbuddy_bridge.ps1 run-pending --runtime-dir D:\CodexProject\Ozon\workbuddy-bridge --concurrency 2
& scripts/workbuddy_bridge.ps1 collect --runtime-dir D:\CodexProject\Ozon\workbuddy-bridge
& scripts/apply_workbuddy_to_workbook.ps1 --workbook D:\CodexProject\Ozon\outputs\run\Ozon上品参考_2026-10-15.xlsx --collected D:\CodexProject\Ozon\workbuddy-bridge\collected-skus.json --runtime-dir D:\CodexProject\Ozon\workbuddy-bridge
```

The PowerShell launcher finds a real Python installation or Codex's bundled Python runtime. For WorkBuddy, the bridge first uses the authenticated standalone executable at `%LOCALAPPDATA%\codebuddy\bin\codebuddy.exe`, then a `codebuddy`/`cbc` command on `PATH`, and only then falls back to the app-embedded entry at `D:\WorkBuddy\resources\app.asar.unpacked\cli\bin\codebuddy`. Override the choice with `--workbuddy-cli` or `WORKBUDDY_CLI` when needed. A `.exe` override runs directly; a JavaScript entry runs through Node.js. The bridge runs WorkBuddy in non-interactive print mode with the extraction prompt and structured-output schema in this skill.

The WorkBuddy CLI has its own authentication state and does not inherit the user's logged-in Chrome cookies. Never copy browser profiles, cookies, local storage, authorization headers, passwords, or tokens into WorkBuddy. When Codex has an attached authenticated 1688 tab, capture only the exact offer's rendered product facts into a browser-evidence JSON conforming to `references/workbuddy-browser-evidence.schema.json`, attach it to the job, and let WorkBuddy parse that local evidence. Verify authenticated access from ordinary product-page signals such as visible stock, complete SKU prices, account navigation, and destination freight; do not inspect unrelated account data. If no attached authenticated page is available, the job may use WorkBuddy's own page access, but it must preserve the weaker access mode and stop for login/CAPTCHA.

For large offers, WorkBuddy writes the complete result to `candidate-results/<job-id>.json` and returns only a small completion envelope. The bridge normalizes only the deterministic SKU display key, validates the candidate, and promotes it into `results/`. This avoids structured-output size failures without weakening validation.

## Controller workflow

1. Complete Ozon selection judgment first. Enqueue only exact 1688 detail URLs for listing-ready A/B candidates.
2. Use one job per offer. Put candidate identity, intended test quantity, intended variants, and the China warehouse destination in the job instead of relying on chat memory.
3. Run at most two or three jobs concurrently. A lower concurrency is preferable when 1688 starts throttling or changing page behavior.
4. Treat each WorkBuddy result as untrusted extraction data. Run the bridge validator and inspect evidence before using it.
5. Retry a `partial` job only for its explicit `missing_fields`; do not repeatedly retry login/CAPTCHA blocks. Ask the user to restore access and then resume the same job.
6. Collect only validated `complete` results by default. `collect` creates `collected-skus.json`, a workbook-ready intermediate with one row per exact purchasable SKU. A `partial` result remains outside the main workbook unless the user explicitly asks for a review-only staging file.
7. Only measurements marked `single_unit_packed` and `high` confidence are automatically eligible for the main workbook logistics columns. Keep other measurements in evidence and apply the pricing reference's proxy rules separately.
8. The collector computes only the China-side cost bounds: executable purchase price + allocated 1688 domestic freight + fixed ¥3 label fee + mandatory charge. It does not calculate cross-border freight or RUB price.
9. Continue pricing from `collected-skus.json` using the current workbooks under `inputs/` and the rules in `sku-pricing-workbook.md`. WorkBuddy must never decide the final price.
10. After the controller fills `suggested_price_rub`, `international_freight_cny`, and `pricing_status`, run `apply_workbuddy_to_workbook.ps1`. It replaces every existing placeholder row for the same exact offer with one row per verified SKU, updates matching rows in `定价依据`, preserves unrelated offers, writes a recoverable backup under the runtime directory, recalculates, scans formula errors, and renders a preview. Inspect the saved nine-column range and preview before delivery.
11. Never let WorkBuddy edit the workbook itself. The deterministic workbook updater is the only writer, and it refuses non-`complete` extraction rows or a workbook missing the required main/pricing headers.

## Failure handling

- `blocked_login` or `blocked_captcha`: stop affected jobs; the user completes authentication manually.
- `invalid_offer`: replace the supplier offer only after rechecking supply fit; do not silently redirect to a different product.
- `partial`: create one targeted retry describing only unresolved fields and variant mappings.
- CLI/process failure: preserve the original job and write a diagnostic under `failed/`; do not fabricate a result.
- Schema or semantic validation failure: quarantine the response under `failed/` and do not merge it.
- Workbook update failure: leave the original workbook unchanged, keep the runtime backup/evidence, and report the exact header, validation, formula, or export blocker.

The runtime directory is working state. Do not place it inside a final run output directory, and do not include its JSON, logs, or screenshots among the two final `.xlsx` deliverables.
