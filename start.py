import os
from dotenv import load_dotenv
import telebot
from PyPDF2 import PdfReader
from openai import OpenAI
import csv
from io import StringIO

# Инициализация Telegram бота
TG_TOKEN = '7594440289:AAGJm4XlDWsS89OkpstGGWYe7WLpt0bFWiU'
bot = telebot.TeleBot(TG_TOKEN)

# Инициализация OpenAI API
load_dotenv() 
client=OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def generate_table_from_text(text):
    # Обновленный запрос с использованием нового интерфейса OpenAI
    prompt = f"""
Извлеки таблицу с двумя колонками: Симптомы и Диагноз. Формат ответа:
- Разделитель колонок — точка с запятой (;).
- Никаких дополнительных текстов, пояснений и кавычек, лишние тоже убери.
- Каждая строка новой записи начинается с новой строки.
- Не используй кавычки (двойные или одинарные) ни вокруг текста, ни в таблице.

Пример формата:  
Симптомы;Диагноз  
Головная боль;Мигрень  
Температура;Грипп  

Текст для анализа: {text}
"""

    completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt, "temperature": 0.2}]
    )
    table = completion.choices[0].message.content.strip()
    
    print("Ответ от OpenAI:", table)  # Логируем ответ

    return table
    

   

def save_table_to_csv(table, filename="output.csv"):
    if not table:  # Проверка на None или пустое значение
        raise ValueError("Получена пустая таблица или None.")
    
    print(table)
    # Разбиваем таблицу на строки и колонки
    lines = table.split("\n")
    data = [line.split("\t") for line in lines if line.strip()]
    
    # Сохраняем данные в файл
    with open(filename, mode="w+", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, quoting=csv.QUOTE_NONE, escapechar=' ', delimiter=';')
        writer.writerows(data)
    
    print(f"Файл сохранён как {filename}")
    return filename

@bot.message_handler(content_types=['document'])
def handle_pdf(message):
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    # Сохранение PDF временно на диск
    with open("temp.pdf", "wb") as f:
        f.write(downloaded_file)
    
    # Извлечение текста из PDF
    text = extract_text_from_pdf("temp.pdf")
    
    # Генерация таблицы из текста
    table = generate_table_from_text(text)
    
    # Сохранение таблицы в CSV
    csv_filename = "output.csv"
    save_table_to_csv(table, filename=csv_filename)  # Сохраняем CSV в файл и закрываем его
    
    # На этом этапе файл CSV гарантированно закрыт
    
    # Открытие файла для отправки
    with open(csv_filename, "rb") as csv_file:
        bot.send_document(message.chat.id, csv_file, caption="Ваша таблица с симптомами и диагнозами.")
    
bot.polling()
