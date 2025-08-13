import json
import os

from sentence_transformers import SentenceTransformer


def read_text_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def split_text_to_paragraphs(text):
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    return paragraphs


def prepare_corpus_and_embeddings(program_names):
    model = SentenceTransformer('all-MiniLM-L6-v2')

    corpus = []
    meta = []

    for program in program_names:
        filename = f"{program}_program_info.txt"
        if not os.path.exists(filename):
            print(f"Файл {filename} не найден, пропускаем")
            continue

        text = read_text_file(filename)
        paragraphs = split_text_to_paragraphs(text)
        corpus.extend(paragraphs)
        meta.extend([program] * len(paragraphs))

    print(f"Всего фрагментов текста: {len(corpus)}")

    if os.path.exists('embeddings.json') and os.path.exists('corpus.json'):
        print("Эмбеддинги и корпус уже существуют. Чтобы пересоздать, удалите файлы embeddings.json и corpus.json")
        return

    print("Начинаю кодирование текста...")
    embeddings = model.encode(corpus, convert_to_tensor=False, show_progress_bar=True)

    with open('corpus.json', 'w', encoding='utf-8') as f:
        json.dump({"texts": corpus, "meta": meta}, f, ensure_ascii=False, indent=2)
    with open('embeddings.json', 'w', encoding='utf-8') as f:
        json.dump(embeddings.tolist(), f)

    print("Корпус и эмбеддинги сохранены")


if __name__ == "__main__":
    prepare_corpus_and_embeddings(['ai', 'ai_product'])
