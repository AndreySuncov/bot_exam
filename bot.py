import json
import numpy as np
import torch

from sentence_transformers import SentenceTransformer, util
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters


with open('corpus.json', 'r', encoding='utf-8') as f:
    corpus_data = json.load(f)

corpus_texts = corpus_data['texts']
corpus_metadata = corpus_data['meta']

with open('embeddings.json', 'r', encoding='utf-8') as f:
    embeddings_list = json.load(f)
embeddings_np = np.array(embeddings_list, dtype=np.float32)
embeddings = torch.tensor(embeddings_np)

model = SentenceTransformer('all-MiniLM-L6-v2')

programs = ['ai', 'ai_product']
RELEVANCE_THRESHOLD = 0.45
MAX_MSG_LEN = 4000


def recommend_electives(background: str, program: str):
    bg = background.lower()
    recs = []

    keywords_ai_advanced = ['программирование', 'python', 'код', 'машинное обучение', 'ml', 'data science']
    keywords_ai_basic = ['новичок', 'начинающий', 'старт', 'основы']

    keywords_ai_product_management = ['маркетинг', 'продукт', 'управление', 'product', 'продажи']
    keywords_ai_product_tech = ['программирование', 'python', 'технологии', 'разработка']

    if program == 'ai':
        if any(word in bg for word in keywords_ai_advanced):
            recs.append("Рекомендуем выбрать курсы по 'Продвинутому машинному обучению' и 'Проектированию систем машинного обучения'.")
        elif any(word in bg for word in keywords_ai_basic):
            recs.append("Для новичков рекомендуем начать с 'Основ машинного обучения' и 'Математики для машинного обучения'.")
        else:
            recs.append("Пожалуйста, уточните ваш уровень знаний по программированию и математике для точной рекомендации.")
    elif program == 'ai_product':
        if any(word in bg for word in keywords_ai_product_management):
            recs.append("Рекомендуем курсы по 'Стратегическому продуктового менеджменту' и 'Метрикам и аналитике продукта'.")
        elif any(word in bg for word in keywords_ai_product_tech):
            recs.append("Рекомендуем изучить 'Основы программирования на Python' и 'Процессы разработки решений на основе ИИ'.")
        else:
            recs.append("Расскажите, пожалуйста, подробнее о вашем бэкграунде для рекомендаций.")

    return "\n".join(recs)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[p] for p in programs]
    examples = (
        "Примеры вопросов, которые можно задать:\n"
        "- У меня опыт в маркетинге, какие курсы по AI Product мне подойдут?\n"
        "- Посоветуй выборные дисциплины, я знаю Python и немного программирую.\n"
        "- Нужно ли профильное образование?"
    )
    await update.message.reply_text(
        "Привет! Выберите программу магистратуры:\n\n" + examples,
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    context.user_data.clear()


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Этот бот помогает выбрать программу магистратуры и подобрать курсы.\n"
        "1. Выберите программу: 'ai' или 'ai_product'.\n"
        "2. Задайте вопрос по программе или расскажите о своем опыте для рекомендаций по выборным дисциплинам.\n"
        "Команды:\n"
        "/start — начать заново\n"
        "/help — помощь"
    )
    await update.message.reply_text(help_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()

    if 'program' not in context.user_data:
        if text in programs:
            context.user_data['program'] = text
            await update.message.reply_text(f"Вы выбрали программу '{text}'. Теперь задайте ваш вопрос по обучению или расскажите о своем опыте для рекомендаций.")
        else:
            keyboard = [[p] for p in programs]
            await update.message.reply_text(
                "Пожалуйста, выберите программу из списка:",
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
        return

    program = context.user_data['program']

    recommendation_keywords = ['рекомендуй', 'выборные', 'дисциплины', 'курсы', 'совет', 'рекомендация']
    experience_keywords = ['опыт', 'знаю', 'учил', 'программирование', 'маркетинг', 'начинающий', 'новичок']

    if any(word in text for word in recommendation_keywords) or any(word in text for word in experience_keywords):
        answer = recommend_electives(text, program)
        await update.message.reply_text(answer)
        return

    query_emb = model.encode(text, convert_to_tensor=True)
    hits = util.semantic_search(query_emb, embeddings, top_k=5)[0]

    filtered_answers = []
    for hit in hits:
        if hit['score'] < RELEVANCE_THRESHOLD:
            continue
        idx = hit['corpus_id']
        if corpus_metadata[idx] == program:
            filtered_answers.append(corpus_texts[idx])

    if not filtered_answers:
        await update.message.reply_text(
            "Извините, не могу найти ответ на этот вопрос.\n"
            "Попробуйте задать вопрос более конкретно или расскажите о вашем опыте, чтобы я мог дать рекомендации."
        )
        return

    response = "\n\n".join(filtered_answers).strip()
    if not response:
        await update.message.reply_text(
            "Извините, не могу найти ответ на этот вопрос.\n"
            "Попробуйте задать вопрос более конкретно или расскажите о вашем опыте."
        )
        return

    for i in range(0, len(response), MAX_MSG_LEN):
        await update.message.reply_text(response[i:i+MAX_MSG_LEN])


if __name__ == "__main__":
    import os
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен")
    app.run_polling()
