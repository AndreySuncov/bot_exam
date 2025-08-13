import csv
import glob
import os


def load_all_tables(program_names):
    all_rows = []
    for program in program_names:
        folder = f"{program}_tables"
        if not os.path.exists(folder):
            print(f"Папка {folder} не найдена, пропускаем")
            continue
        files = glob.glob(os.path.join(folder, '*.csv'))
        for file in files:
            with open(file, encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if any(cell.strip() for cell in row):
                        all_rows.append(row)
    print(f"Загружено строк из таблиц: {len(all_rows)}")
    return all_rows


def find_courses_by_keyword(rows, keyword):
    keyword = keyword.lower()
    results = []
    for row in rows:
        for cell in row:
            if keyword in cell.lower():
                results.append(row)
                break
    return results


if __name__ == "__main__":
    rows = load_all_tables(['ai', 'ai_product'])
    query = input("Введите ключевое слово для поиска по таблицам: ").strip()
    found = find_courses_by_keyword(rows, query)
    print(f"Найдено {len(found)} строк:")
    for row in found[:10]:
        print(row)
