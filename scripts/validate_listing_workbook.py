#!/usr/bin/env python3
"""Validate the fixed nine-column Ozon listing-reference sheet before delivery."""

from __future__ import annotations

import re
import sys
from math import ceil, isfinite
from pathlib import Path

from openpyxl import load_workbook


EXPECTED_HEADERS = [
    "sku",
    "自定义货号",
    "重量（g）",
    "长度（mm）",
    "宽度（mm）",
    "高度（mm）",
    "商品详情页链接",
    "成本价",
    "建议售价",
]
DETAIL_URL = re.compile(r"^https://detail\.1688\.com/offer/\d+\.html(?:[?#].*)?$")
REQUIRED_PRICING_HEADERS = [
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
]


def has_cny_unit(value: object, number_format: str) -> bool:
    if isinstance(value, (int, float)):
        return "¥" in number_format or "CNY" in number_format.upper()
    text = str(value or "")
    return "¥" in text or "CNY" in text.upper()


def has_rub_unit(number_format: str) -> bool:
    return "₽" in number_format or "RUB" in number_format.upper()


def find_header_row(sheet) -> int:
    for row in range(1, min(sheet.max_row, 50) + 1):
        values = [sheet.cell(row, col).value for col in range(1, 10)]
        if values == EXPECTED_HEADERS:
            return row
    raise ValueError("未找到完全匹配的九列表头")


def find_pricing_header(sheet) -> tuple[int, dict[str, int]]:
    for row in range(1, min(sheet.max_row, 60) + 1):
        mapping = {
            str(sheet.cell(row, col).value).strip(): col
            for col in range(1, sheet.max_column + 1)
            if sheet.cell(row, col).value not in (None, "")
        }
        if all(header in mapping for header in REQUIRED_PRICING_HEADERS):
            return row, mapping
    raise ValueError("定价依据缺少成本拆分必需列")


def as_number(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def is_positive_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
        and float(value) > 0
    )


def completion_summary(rows: list[list[object]]) -> dict[str, object]:
    fields = {
        "重量（g）": 2,
        "长度（mm）": 3,
        "宽度（mm）": 4,
        "高度（mm）": 5,
        "建议售价": 8,
    }
    field_counts = {
        name: sum(is_positive_number(row[index]) for row in rows)
        for name, index in fields.items()
    }
    complete = sum(
        all(is_positive_number(row[index]) for index in fields.values())
        for row in rows
    )
    total = len(rows)
    return {
        "total": total,
        "complete": complete,
        "required": ceil(total * 0.90),
        "ratio": (complete / total) if total else 0.0,
        "field_counts": field_counts,
    }


def validate(path: Path) -> list[str]:
    workbook = load_workbook(path, data_only=False, read_only=False)
    if "Ozon上品参考" not in workbook.sheetnames:
        return ["缺少工作表：Ozon上品参考"]
    sheet = workbook["Ozon上品参考"]
    errors: list[str] = []
    try:
        header_row = find_header_row(sheet)
    except ValueError as exc:
        return [str(exc)]

    populated_rows: list[list[object]] = []
    for row in range(header_row + 1, sheet.max_row + 1):
        values = [sheet.cell(row, col).value for col in range(1, 10)]
        if all(value in (None, "") for value in values):
            continue
        populated_rows.append(values)
        if not values[0] or not values[1]:
            errors.append(f"第{row}行：sku或自定义货号为空")
        for col in range(3, 7):
            value = values[col - 1]
            if value not in (None, "") and not isinstance(value, (int, float)):
                errors.append(f"第{row}行：{sheet.cell(header_row, col).value}必须为空或数值")
        link = values[6]
        if not isinstance(link, str) or not DETAIL_URL.match(link.strip()):
            errors.append(f"第{row}行：G列不是有效1688详情链接")
        for col in [3, 4, 5, 6, 8, 9]:
            value = values[col - 1]
            if isinstance(value, str) and value.lower().startswith(("http://", "https://")):
                errors.append(f"第{row}行：链接错误地出现在{sheet.cell(header_row, col).value}列")
        cost_cell = sheet.cell(row, 8)
        if cost_cell.value in (None, ""):
            errors.append(f"第{row}行：成本价为空")
        elif not has_cny_unit(cost_cell.value, cost_cell.number_format or ""):
            errors.append(f"第{row}行：成本价未显示CNY/¥单位")
        price_cell = sheet.cell(row, 9)
        if price_cell.value not in (None, ""):
            if not isinstance(price_cell.value, (int, float)):
                errors.append(f"第{row}行：建议售价必须为数值或留空")
            elif not has_rub_unit(price_cell.number_format or ""):
                errors.append(f"第{row}行：建议售价未显示RUB/₽单位")

    completion = completion_summary(populated_rows)
    if completion["total"] == 0:
        errors.append("Ozon上品参考没有商品SKU数据行")
    elif completion["complete"] < completion["required"]:
        field_text = "，".join(
            f"{name}{count}/{completion['total']}"
            for name, count in completion["field_counts"].items()
        )
        errors.append(
            "五项联合完整率不足90%："
            f"完整{completion['complete']}/{completion['total']}"
            f"（{completion['ratio']:.1%}），至少需要{completion['required']}行；"
            f"各字段：{field_text}"
        )

    if "定价依据" not in workbook.sheetnames:
        errors.append("缺少工作表：定价依据")
        return errors
    pricing = workbook["定价依据"]
    try:
        pricing_header_row, columns = find_pricing_header(pricing)
    except ValueError as exc:
        errors.append(str(exc))
        return errors

    for row in range(pricing_header_row + 1, pricing.max_row + 1):
        item_no = pricing.cell(row, columns["自定义货号"]).value
        if item_no in (None, ""):
            continue
        numeric_headers = REQUIRED_PRICING_HEADERS[1:11]
        numbers: dict[str, float] = {}
        for header in numeric_headers:
            value = as_number(pricing.cell(row, columns[header]).value)
            if value is None:
                errors.append(f"定价依据第{row}行：{header}必须为数值")
            else:
                numbers[header] = value
        if numbers.get("贴单费(CNY)") != 3:
            errors.append(f"定价依据第{row}行：贴单费必须为3元")
        required_math = {
            "采购价下限(CNY)", "采购价上限(CNY)",
            "国内运费下限(CNY)", "国内运费上限(CNY)",
            "贴单费(CNY)", "其他国内成本(CNY)",
            "成本价下限(CNY)", "成本价上限(CNY)",
        }
        if required_math.issubset(numbers):
            expected_low = (
                numbers["采购价下限(CNY)"] + numbers["国内运费下限(CNY)"]
                + numbers["贴单费(CNY)"] + numbers["其他国内成本(CNY)"]
            )
            expected_high = (
                numbers["采购价上限(CNY)"] + numbers["国内运费上限(CNY)"]
                + numbers["贴单费(CNY)"] + numbers["其他国内成本(CNY)"]
            )
            if abs(numbers["成本价下限(CNY)"] - expected_low) > 0.011:
                errors.append(f"定价依据第{row}行：成本价下限加总不正确")
            if abs(numbers["成本价上限(CNY)"] - expected_high) > 0.011:
                errors.append(f"定价依据第{row}行：成本价上限加总不正确")
            if numbers["成本价下限(CNY)"] > numbers["成本价上限(CNY)"]:
                errors.append(f"定价依据第{row}行：成本价下限高于上限")
    return errors


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) != 2:
        print("用法: validate_listing_workbook.py <Ozon上品参考.xlsx>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1]).expanduser().resolve()
    if not path.is_file():
        print(f"文件不存在: {path}", file=sys.stderr)
        return 2
    errors = validate(path)
    if errors:
        print("校验失败:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("校验通过：九列位置、货币单位和五项联合完整率均符合要求。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
