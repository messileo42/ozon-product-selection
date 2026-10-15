#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { createRequire } from "node:module";

const moduleRoot = process.env.CODEX_WORKSPACE_NODE_MODULES;
if (!moduleRoot) {
  throw new Error("缺少CODEX_WORKSPACE_NODE_MODULES；请通过apply_workbuddy_to_workbook.ps1启动");
}
const require = createRequire(path.join(moduleRoot, "package.json"));
const { FileBlob, SpreadsheetFile } = require("@oai/artifact-tool");

const MAIN_HEADERS = [
  "sku",
  "自定义货号",
  "重量（g）",
  "长度（mm）",
  "宽度（mm）",
  "高度（mm）",
  "商品详情页链接",
  "成本价",
  "建议售价",
];
const PRICING_HEADERS = [
  "自定义货号",
  "采购价下限(CNY)",
  "采购价上限(CNY)",
  "国内运费下限(CNY)",
  "国内运费上限(CNY)",
  "贴单费(CNY)",
  "其他国内成本(CNY)",
  "成本价下限(CNY)",
  "成本价上限(CNY)",
  "国际运费(CNY)",
  "建议售价(RUB)",
  "定价状态",
];

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith("--")) throw new Error(`无法识别的参数：${token}`);
    const name = token.slice(2);
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`参数--${name}缺少值`);
    args[name] = value;
    index += 1;
  }
  for (const required of ["workbook", "collected", "runtime-dir"]) {
    if (!args[required]) throw new Error(`缺少参数--${required}`);
  }
  return args;
}

function findHeaderRow(matrix, headers) {
  return matrix.findIndex((row) => headers.every((header, index) => row[index] === header));
}

function lastPopulatedRow(matrix, startRow, width) {
  let last = startRow - 1;
  for (let index = startRow; index < matrix.length; index += 1) {
    if ((matrix[index] ?? []).slice(0, width).some((value) => value !== null && value !== "")) {
      last = index;
    }
  }
  return last;
}

function canonicalOffer(value) {
  const match = String(value ?? "").match(/^https:\/\/detail\.1688\.com\/offer\/(\d+)\.html(?:[?#].*)?$/);
  return match ? `https://detail.1688.com/offer/${match[1]}.html` : null;
}

function makePrefix(row, oldRows) {
  const requested = String(row.custom_item_prefix ?? "").toUpperCase();
  if (/^[A-Z]{1,4}$/.test(requested)) return requested;
  for (const old of oldRows) {
    const match = String(old[1] ?? "").match(/^([A-Z]{1,4})\d{4}$/);
    if (match) return match[1];
  }
  const fallback = String(row.candidate_id ?? "SKU").toUpperCase().replace(/[^A-Z]/g, "").slice(0, 4);
  return fallback || "SKU";
}

function nextCustomItem(prefix, used) {
  let maximum = 0;
  for (const value of used) {
    const match = String(value).match(new RegExp(`^${prefix}(\\d{4})$`));
    if (match) maximum = Math.max(maximum, Number(match[1]));
  }
  for (let number = maximum + 1; number <= 9999; number += 1) {
    const value = `${prefix}${String(number).padStart(4, "0")}`;
    if (!used.has(value)) {
      used.add(value);
      return value;
    }
  }
  throw new Error(`自定义货号前缀${prefix}已无可用四位序号`);
}

function toMainRecord(row, customItemNo) {
  const cost =
    typeof row.cost_price_upper_cny === "number" &&
    Math.abs(row.cost_price_upper_cny - row.cost_price_lower_cny) < 0.005
      ? row.cost_price_lower_cny
      : row.cost_price_display;
  const values = [
    row.sku,
    customItemNo,
    row.weight_g ?? null,
    row.length_mm ?? null,
    row.width_mm ?? null,
    row.height_mm ?? null,
    canonicalOffer(row.product_detail_url),
    cost,
    typeof row.suggested_price_rub === "number" ? row.suggested_price_rub : null,
  ];
  if (values.length !== 9 || !values[0] || !values[1] || !values[6]) {
    throw new Error(`SKU ${row.sku ?? "<unknown>"} 无法构造九列主表记录`);
  }
  return values;
}

function pricingRecord(row, customItemNo, headers) {
  const mapping = {
    "自定义货号": customItemNo,
    "采购价下限(CNY)": row.purchase_price_cny,
    "采购价上限(CNY)": row.purchase_price_cny,
    "国内运费下限(CNY)": row.domestic_freight_lower_cny,
    "国内运费上限(CNY)": row.domestic_freight_upper_cny,
    "贴单费(CNY)": row.label_fee_cny,
    "其他国内成本(CNY)": row.mandatory_charge_cny,
    "成本价下限(CNY)": row.cost_price_lower_cny,
    "成本价上限(CNY)": row.cost_price_upper_cny,
    "国际运费(CNY)": row.international_freight_cny,
    "建议售价(RUB)": row.suggested_price_rub,
    "定价状态": row.suggested_price_rub == null ? "暂停" : row.pricing_status,
    "sku": row.sku,
    "1688链接": canonicalOffer(row.product_detail_url),
    "商品详情页链接": canonicalOffer(row.product_detail_url),
    "MOQ": row.purchase_min_qty,
    "采购单位": row.purchase_unit,
    "包装数据范围": row.measurement_scope,
    "包装数据置信度": row.measurement_confidence,
    "包装原文": row.measurement_raw_text,
    "抓取时间": row.source_observed_at,
    "抓取状态": row.source_status,
    "访问模式": row.access_mode,
  };
  return headers.map((header) => Object.hasOwn(mapping, header) ? mapping[header] ?? null : null);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const workbookPath = path.resolve(args.workbook);
  const collectedPath = path.resolve(args.collected);
  const runtimeDir = path.resolve(args["runtime-dir"]);
  const outputPath = path.resolve(args.output ?? workbookPath);
  const collected = JSON.parse(await fs.readFile(collectedPath, "utf8"));
  const sourceRows = collected.rows ?? [];
  if (!Array.isArray(sourceRows) || sourceRows.length === 0) {
    throw new Error("汇总数据没有可回写SKU")
  }
  const invalidStatuses = [...new Set(sourceRows.map((row) => row.source_status).filter((value) => value !== "complete"))];
  if (invalidStatuses.length) {
    throw new Error(`仅允许回写complete结果；发现：${invalidStatuses.join(", ")}`);
  }

  const input = await FileBlob.load(workbookPath);
  const workbook = await SpreadsheetFile.importXlsx(input);
  const mainSheet = workbook.worksheets.getItem("Ozon上品参考");
  const pricingSheet = workbook.worksheets.getItem("定价依据");
  if (!mainSheet || !pricingSheet) throw new Error("工作簿必须包含Ozon上品参考和定价依据")

  const mainMatrix = mainSheet.getUsedRange().values;
  const mainHeader = findHeaderRow(mainMatrix, MAIN_HEADERS);
  if (mainHeader < 0) throw new Error("Ozon上品参考未找到固定九列表头")
  const mainLast = lastPopulatedRow(mainMatrix, mainHeader + 1, 9);
  const oldMainRows = mainLast >= mainHeader + 1
    ? mainMatrix.slice(mainHeader + 1, mainLast + 1).map((row) => MAIN_HEADERS.map((_, index) => row[index] ?? null))
    : [];

  const grouped = new Map();
  for (const row of sourceRows) {
    const url = canonicalOffer(row.product_detail_url);
    if (!url) throw new Error(`无效1688详情页链接：${row.product_detail_url}`);
    if (!grouped.has(url)) grouped.set(url, []);
    grouped.get(url).push(row);
  }
  const oldByUrl = new Map();
  for (const row of oldMainRows) {
    const url = canonicalOffer(row[6]);
    if (!url) continue;
    if (!oldByUrl.has(url)) oldByUrl.set(url, []);
    oldByUrl.get(url).push(row);
  }
  const replacedUrls = new Set(grouped.keys());
  const removedCustomItems = new Set(
    oldMainRows
      .filter((row) => replacedUrls.has(canonicalOffer(row[6])))
      .map((row) => row[1])
      .filter(Boolean),
  );
  const usedCustomItems = new Set(
    oldMainRows
      .filter((row) => !replacedUrls.has(canonicalOffer(row[6])))
      .map((row) => row[1])
      .filter(Boolean),
  );
  const newRowsByUrl = new Map();
  const pricingInputs = [];
  for (const [url, rows] of grouped) {
    const priorRows = oldByUrl.get(url) ?? [];
    const priorBySku = new Map(priorRows.map((row) => [row[0], row[1]]));
    const prefix = makePrefix(rows[0], priorRows);
    const created = rows.map((row) => {
      let customItemNo = row.custom_item_no || priorBySku.get(row.sku);
      if (!customItemNo || (usedCustomItems.has(customItemNo) && !priorBySku.has(row.sku))) {
        customItemNo = nextCustomItem(prefix, usedCustomItems);
      } else {
        usedCustomItems.add(customItemNo);
      }
      pricingInputs.push({ row, customItemNo });
      return toMainRecord(row, customItemNo);
    });
    newRowsByUrl.set(url, created);
  }

  const emitted = new Set();
  const updatedMainRows = [];
  for (const row of oldMainRows) {
    const url = canonicalOffer(row[6]);
    if (url && newRowsByUrl.has(url)) {
      if (!emitted.has(url)) updatedMainRows.push(...newRowsByUrl.get(url));
      emitted.add(url);
    } else {
      updatedMainRows.push(row);
    }
  }
  for (const [url, rows] of newRowsByUrl) {
    if (!emitted.has(url)) updatedMainRows.push(...rows);
  }
  const clearMainCount = Math.max(oldMainRows.length, updatedMainRows.length);
  if (clearMainCount > 0) {
    mainSheet.getRangeByIndexes(mainHeader + 1, 0, clearMainCount, 9).clear({ applyTo: "contents" });
  }
  mainSheet.getRangeByIndexes(mainHeader + 1, 0, updatedMainRows.length, 9).values = updatedMainRows;
  mainSheet.getRangeByIndexes(mainHeader + 1, 2, updatedMainRows.length, 4).format.numberFormat = "0";
  mainSheet.getRangeByIndexes(mainHeader + 1, 7, updatedMainRows.length, 1).format.numberFormat = '"¥"#,##0.00';
  mainSheet.getRangeByIndexes(mainHeader + 1, 8, updatedMainRows.length, 1).format.numberFormat = '"₽"#,##0';
  const mainWidths = [28, 14, 12, 12, 12, 12, 48, 22, 14];
  mainWidths.forEach((width, index) => {
    mainSheet.getRangeByIndexes(mainHeader, index, updatedMainRows.length + 1, 1).format.columnWidth = width;
  });

  const pricingMatrix = pricingSheet.getUsedRange().values;
  const pricingHeader = findHeaderRow(pricingMatrix, PRICING_HEADERS);
  if (pricingHeader < 0) throw new Error("定价依据未找到必需的12列表头")
  const pricingHeaders = pricingMatrix[pricingHeader].map((value) => value ?? "");
  const pricingWidth = pricingHeaders.length;
  const pricingLast = lastPopulatedRow(pricingMatrix, pricingHeader + 1, pricingWidth);
  const oldPricingRows = pricingLast >= pricingHeader + 1
    ? pricingMatrix.slice(pricingHeader + 1, pricingLast + 1).map((row) => pricingHeaders.map((_, index) => row[index] ?? null))
    : [];
  const customIndex = pricingHeaders.indexOf("自定义货号");
  const retainedPricingRows = oldPricingRows.filter((row) => !removedCustomItems.has(row[customIndex]));
  const newPricingRows = pricingInputs.map(({ row, customItemNo }) => pricingRecord(row, customItemNo, pricingHeaders));
  const updatedPricingRows = [...retainedPricingRows, ...newPricingRows];
  const clearPricingCount = Math.max(oldPricingRows.length, updatedPricingRows.length);
  if (clearPricingCount > 0) {
    pricingSheet.getRangeByIndexes(pricingHeader + 1, 0, clearPricingCount, pricingWidth).clear({ applyTo: "contents" });
  }
  pricingSheet.getRangeByIndexes(pricingHeader + 1, 0, updatedPricingRows.length, pricingWidth).values = updatedPricingRows;

  workbook.recalculate();
  const inspected = await workbook.inspect({
    kind: "table",
    range: `Ozon上品参考!A${mainHeader + 1}:I${mainHeader + 1 + Math.min(updatedMainRows.length, 40)}`,
    include: "values,formulas",
    tableMaxRows: 45,
    tableMaxCols: 9,
    maxChars: 12000,
  });
  const formulaErrors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
    options: { useRegex: true, maxResults: 100 },
    summary: "workbuddy workbook update formula error scan",
  });
  if (formulaErrors.ndjson && /#REF!|#DIV\/0!|#VALUE!|#NAME\?|#N\/A|#NUM!|#NULL!|#SPILL!|#CALC!/.test(formulaErrors.ndjson)) {
    throw new Error(`回写后发现公式错误：${formulaErrors.ndjson.slice(0, 2000)}`);
  }

  await fs.mkdir(runtimeDir, { recursive: true });
  const preview = await workbook.render({
    sheetName: "Ozon上品参考",
    range: `A1:I${Math.min(mainHeader + 1 + updatedMainRows.length, 45)}`,
    scale: 1,
    format: "png",
  });
  const previewPath = path.join(runtimeDir, "workbook-update-preview.png");
  await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));

  const exported = await SpreadsheetFile.exportXlsx(workbook);
  if (outputPath === workbookPath) {
    const backupDir = path.join(runtimeDir, "backups");
    await fs.mkdir(backupDir, { recursive: true });
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    await fs.copyFile(workbookPath, path.join(backupDir, `${path.basename(workbookPath, ".xlsx")}-${stamp}.xlsx`));
    const tempPath = path.join(runtimeDir, `${path.basename(workbookPath, ".xlsx")}.updated.tmp.xlsx`);
    await exported.save(tempPath);
    await fs.copyFile(tempPath, workbookPath);
    await fs.unlink(tempPath);
  } else {
    await fs.mkdir(path.dirname(outputPath), { recursive: true });
    await exported.save(outputPath);
  }
  console.log(JSON.stringify({
    output: outputPath,
    preview: previewPath,
    updated_offers: grouped.size,
    updated_skus: pricingInputs.length,
    main_rows: updatedMainRows.length,
    pricing_rows: updatedPricingRows.length,
    inspect: inspected.ndjson,
  }, null, 2));
}

await main();
