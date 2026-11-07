import csv
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SOURCE_DIR = BASE_DIR / "data"
DESTINATION_DIR = BASE_DIR / "_data-json_"

INTEGER_FIELDS = {
    "product_id",
    "category_id",
    "stock_quantity",
    "customer_id",
    "order_id",
    "quantity",
    "promotion_id",
    "discount_percent",
}
DECIMAL_FIELDS = {"price_brl", "total_brl"}


def convert_value(field, value):
    if value == "":
        return None
    if field == "specs":
        return json.loads(value)
    if field == "is_active":
        return value == "1"
    if field in INTEGER_FIELDS:
        return int(value)
    if field in DECIMAL_FIELDS:
        return float(value)
    return value


def convert_csv(csv_path, json_path):
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        records = [
            {
                field: convert_value(field, value)
                for field, value in row.items()
            }
            for row in reader
        ]

    with json_path.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)
        file.write("\n")


def main():
    DESTINATION_DIR.mkdir(exist_ok=True)
    csv_files = sorted(SOURCE_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"Nenhum arquivo CSV encontrado em {SOURCE_DIR}")

    for csv_path in csv_files:
        json_path = DESTINATION_DIR / f"{csv_path.stem}.json"
        convert_csv(csv_path, json_path)
        print(f"Convertido: {csv_path.name} -> {json_path.name}")


if __name__ == "__main__":
    main()
