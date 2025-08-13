import csv
import json
import os
import pdfplumber
import requests

from bs4 import BeautifulSoup
from requests.exceptions import RequestException


def get_next_data_json(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except RequestException as e:
        print(f"Ошибка загрузки страницы: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    script_tag = soup.find('script', id='__NEXT_DATA__')
    if not script_tag:
        print("Тег <script id='__NEXT_DATA__'> не найден")
        return None

    json_text = script_tag.string
    if not json_text:
        print("JSON внутри <script> пуст")
        return None

    data = json.loads(json_text)
    return data


def extract_academic_plan_url(data):
    api_program = data.get('props', {}).get('pageProps', {}).get('apiProgram', {})
    academic_plan_url = api_program.get('academic_plan')
    if academic_plan_url:
        print(f"Найдена ссылка на учебный план: {academic_plan_url}")
    else:
        print("Ссылка на учебный план не найдена")
    return academic_plan_url


def download_pdf(url, filename):
    print(f"Скачиваем PDF: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"Файл сохранён: {filename}")
        return filename
    except RequestException as e:
        print(f"Ошибка загрузки PDF: {e}")
        return None


def parse_pdf_text(filename):
    print(f"Парсим PDF: {filename}")
    all_text = []
    with pdfplumber.open(filename) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                all_text.append(text)
    full_text = "\n".join(all_text)
    print(f"Извлечено текста: {len(full_text)} символов")
    return full_text


def extract_tables_from_pdf(pdf_path, output_folder="tables"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    total_tables = 0
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            if tables:
                print(f"Найдено {len(tables)} таблиц на странице {i}")
                for j, table in enumerate(tables, start=1):
                    csv_filename = os.path.join(output_folder, f"table_page_{i}_num_{j}.csv")
                    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        for row in table:
                            writer.writerow(row)
                    print(f"Таблица сохранена: {csv_filename}")
                    total_tables += 1
            else:
                print(f"Таблиц на странице {i} не найдено")

    print(f"Всего сохранено таблиц: {total_tables}")


def process_program(url, program_name):
    print(f"\n=== Обработка программы: {program_name} ===")
    data = get_next_data_json(url)
    if not data:
        print("Ошибка при получении данных JSON")
        return None

    save_program_text_data(data, program_name)

    academic_plan_url = extract_academic_plan_url(data)
    if not academic_plan_url:
        print("Учебный план не найден")
        return None

    pdf_filename = f"{program_name}_academic_plan.pdf"
    if not download_pdf(academic_plan_url, pdf_filename):
        print("Ошибка при скачивании PDF")
        return None

    pdf_text = parse_pdf_text(pdf_filename)

    tables_folder = f"{program_name}_tables"
    extract_tables_from_pdf(pdf_filename, tables_folder)

    return {
        "program": program_name,
        "url": url,
        "academic_plan_pdf_url": academic_plan_url,
        "academic_plan_text_preview": pdf_text[:2000],
        "tables_folder": tables_folder
    }


def save_program_text_data(data, program_name):
    api_program = data.get('props', {}).get('pageProps', {}).get('apiProgram', {})
    json_program = data.get('props', {}).get('pageProps', {}).get('jsonProgram', {})

    lines = []

    title = api_program.get('title') or json_program.get('title') or program_name
    lines.append(f"Название программы: {title}\n")

    text_fields = ['about', 'career', 'social', 'foreign', 'achievements', 'faq']

    for field in text_fields:
        content = json_program.get(field)
        if content:
            lines.append(f"--- {field.upper()} ---\n")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        question = item.get('question') or item.get('title') or ''
                        answer = item.get('answer') or item.get('text') or ''
                        lines.append(f"Вопрос: {question}\nОтвет: {answer}\n")
                    else:
                        lines.append(str(item) + "\n")
            elif isinstance(content, dict):
                for k, v in content.items():
                    lines.append(f"{k}: {v}")
                lines.append("")
            else:
                lines.append(str(content) + "\n")

    filename = f"{program_name}_program_info.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(line + '\n' for line in lines)
    print(f"Текстовая информация программы сохранена в {filename}")


if __name__ == "__main__":
    programs = {
        "ai": "https://abit.itmo.ru/program/master/ai",
        "ai_product": "https://abit.itmo.ru/program/master/ai_product"
    }

    results = []

    for name, url in programs.items():
        result = process_program(url, name)
        if result:
            results.append(result)

    save_filename = "study_plans_results.json"
    with open(save_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nОбработка завершена. Результаты сохранены в {save_filename}")
