import os
from dotenv import load_dotenv
import telebot
from PyPDF2 import PdfReader
from openai import OpenAI
import csv
import re
from io import StringIO

# Инициализация Telegram бота
TG_TOKEN = '7594440289:AAGJm4XlDWsS89OkpstGGWYe7WLpt0bFWiU'
bot = telebot.TeleBot(TG_TOKEN)

# Инициализация OpenAI API
load_dotenv() 
client=OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)
def clean_text(text):
    # Убираем все символы, которые не являются обычными буквами, цифрами и пробелами
    cleaned_text = re.sub(r'[^\w\s,;.:]', '', text)  # Оставляем только текст, цифры и базовые знаки
    cleaned_text = ' '.join(cleaned_text.split())  # Убираем лишние пробелы
    return cleaned_text
def generate_table_from_instruction(text, instructions):
    text=clean_text(text)
    # Формируем финальный промпт
    prompt = f"""
        Вот запрос пользователя:{instructions}
        Вот опираясь на что нужно дать ответ (не смущайся если пользователь назовет это файлом): {text}
    """

    try:
        # Отправляем запрос к OpenAI
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        # Извлекаем результат
        table = completion.choices[0].message.content.strip()
        print("Ответ от OpenAI:", table)  # Логируем ответ
        return table
    except Exception as e:
        print(f"Ошибка при генерации таблицы: {e}")
        raise

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        textfrompage = page.extract_text()
        cleartext= clean_text(textfrompage)
        text += cleartext
    return text
def generate_dynamic_prompt(text, instruction):
    # Извлекаем ключевые слова из инструкции
    prompt="notfile"
    if instruction is None:
        # Если инструкция не подходит под таблицу или пересказ, выводим общий запрос
        prompt = f"""
        Извлеки таблицу с двумя колонками: Симптомы и Диагноз. Формат ответа:
        - Разделитель колонок — точка с запятой (;).
        - Никаких дополнительных текстов, пояснений и кавычек, лишние тоже убери.
        - Каждая строка новой записи начинается с новой строки.
        - Не используй кавычки (двойные или одинарные) ни вокруг текста, ни в таблице.
        - Не забывай, что симптомов может быть несколько, так же как и диагнозов

        Пример формата:  
        Симптомы;Диагноз  
        Симптом1,симптом2,симптомN;Диагноз
        Температура, лихорадка;Грипп  

        Текст для анализа: {text}

        """
    else:
        if 'таблицу' in instruction.lower():
            # Извлечение названий столбцов из инструкции
            match = re.search(r'столбцы: (.+)', instruction.lower())
            if match:
                columns = match.group(1).strip()  # Получаем названия колонок
                columns_list = [col.strip().capitalize() for col in columns.split(',')]  # Преобразуем их в список
                columns_str = ';'.join(columns_list)  # Формируем строку для CSV

                # Создаем запрос для формирования таблицы
                prompt = f"""
                Извлеки таблицу с колонками: {columns_str}. Формат ответа:
                - Первой строкой обязательно должно быть CSV.
                - Разделитель колонок — точка с запятой (;).
                - Никаких дополнительных текстов, пояснений и кавычек.
                - Каждая строка новой записи начинается с новой строки.
                - Не используй кавычки (двойные или одинарные) ни вокруг текста, ни в таблице.

                Пример формата:
                CSV:
                {columns_str}
                первый столбец;второй;третий
                данные первого столбца;второго;третьего

                Текст для анализа: {text}
                """
        elif "пересказ" in instruction.lower() or "резюмируй" in instruction.lower():
            # Формируем запрос для краткого пересказа
            match = re.search(r'\d+', instruction)
            number = match.group(0) if match else 1  # Если число найдено, сохраняем его в переменную, иначе None
            prompt = f"""
            Составь пересказ текста на {number} страниц. 
            Первой строкой обязательно написать TXT, а затем, начиная с новой строки, пересказ текста на {number} Страниц А4.

            Текст для анализа: {text}
            """
    return prompt
def generate_table_from_text(text, instructions):
    # Обновленный запрос с использованием нового интерфейса OpenAI
    #можно добавить обработчик пустой инструкции
    prompt = generate_dynamic_prompt(text, instructions)

    completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt, "temperature": 0.7}]
    )
    table = completion.choices[0].message.content.strip()
    
    print("Ответ от OpenAI:", table)  # Логируем ответ

    return table
    

   

def save_table_to_csv(table, filename="output.csv"):
    if not table:  # Проверка на None или пустое значение
        raise ValueError("Получена пустая таблица или None.")
    
    # Разбиваем таблицу на строки
    lines = table.split("\n")
    
    # Преобразуем строки в списки столбцов
    data = []
    for line in lines:
        if line.strip():  # Пропускаем пустые строки
            # Разделяем строку на столбцы по табуляции (или другому символу)
            columns = line.split("\t")
            data.append(columns)
    
    # Проверяем, есть ли минимальные столбцы в первой строке для правильного CSV
    max_columns = max(len(columns) for columns in data)  # Максимальное количество столбцов в строках
    for i in range(len(data)):
        while len(data[i]) < max_columns:  # Если колонок меньше максимального, добавляем пустые значения
            data[i].append("")
    
    # Сохраняем данные в файл
    with open(filename, mode="w+", newline="", encoding="utf-8") as file:
        writer = csv.writer(file, quoting=csv.QUOTE_NONE, escapechar=' ', delimiter=';')
        writer.writerows(data)
    
    print(f"Файл сохранён как {filename}")
    return filename
@bot.message_handler(commands=['start'])
def handle_start(message):
    """Обработчик команды /start."""
    bot.send_message(
        message.chat.id, 
        "Привет! Я помогу вам извлечь данные из PDF и обработать их. Вот что я умею:\n\n"
        "1️⃣ Загрузите PDF файл(Обязательно!).\n"
        "2️⃣ Отправьте текстовую инструкцию для обработки данных из файла. Советую так же ознакомиться с инструкцией /help.\n\n"
        "Если у вас есть вопросы, просто начните диалог!"
    )
@bot.message_handler(commands=['help'])
def handle_help(message):
    """обработчик команды /help"""
    bot.send_message(message.chat.id,
                     """Привет! Я помогу вам разобраться, как работает бот и какие действия доступны:\n\n
Пример логической цепочки взаимодействия:\n
📂 1️⃣ Вы загружаете PDF файл (обязательно!).\n
💾 2️⃣ Программа сохраняет файл в контекст, чтобы он оставался доступным для последующих взаимодействий.\n
🔄 3️⃣ При повторных визитах вы можете продолжить работу с тем же файлом — он уже сохранен.\n \n 
⚙️ Чтобы бот вернул вам таблицу CSV вам нужно указать в чат следующее "Выведи таблицу поделенную на столбцы: Столбец1, столбец2, столбецN" \n 
⚙️ Чтобы бот сделал вам краткий пересказ файла можете написать "пересказ" или "резюмируй".\n
😌 В остальном можете свободно писать любой запрос и бот ответит вам так, как только сможет:)""")

@bot.message_handler(content_types=['document', 'text'])
def handle_message(message):
    if message.content_type == 'document':  # Если сообщение содержит документ
        if message.document.mime_type == 'application/pdf':  # Проверяем, что это PDF
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)

            # Сохраняем PDF временно на диск
            with open("temp.pdf", "wb") as f:
                f.write(downloaded_file)

            bot.send_message(message.chat.id, "Файл успешно сохранён. Теперь вы можете отправить текстовую инструкцию для обработки файла.")
        else:
            bot.send_message(message.chat.id, "Этот тип файла не поддерживается. Пожалуйста, отправьте PDF.")

    elif message.content_type == 'text':  # Если сообщение содержит текст
        text_message = message.text.strip()
        if text_message:
            if os.path.exists("temp.pdf"):
                # Извлечение текста из ранее сохранённого PDF
                text = extract_text_from_pdf("temp.pdf")

                instructions = text_message
                bot.send_message(message.chat.id, f"Сейчас постараюсь выполнить вашу просьбу: '\n{instructions}'")
                filechoiser=generate_dynamic_prompt(text, instructions)
                if(filechoiser!="notfile"):#Если файл
                    print("TXT OR CSV")
                    answer = generate_table_from_text(text, instructions)
                    if answer.startswith("CSV"):
                        answer = re.sub(r'^[^\n]*\n', '', answer)
                        csv_filename = "output.csv"
                        save_table_to_csv(answer, filename=csv_filename)
                        with open(csv_filename, "rb") as csv_file:
                            bot.send_document(message.chat.id, csv_file, caption="Ваш результат в формате CSV.")
                    elif answer.startswith("TXT"):
                        txt_filename = "output.txt"
                        answer = re.sub(r'^[^\n]*\n', '', answer)
                        with open(txt_filename, "w", encoding="utf-8") as txt_file:
                            txt_file.write(answer)
                        with open(txt_filename, "rb") as txt_file:
                            bot.send_document(message.chat.id, txt_file, caption="Ваш текстовый результат.")

                else:
                    answer = generate_table_from_instruction(text, instructions)
                    if answer.startswith("CSV"):
                        csv_filename = "output.csv"
                        save_table_to_csv(answer, filename=csv_filename)
                        with open(csv_filename, "rb") as csv_file:
                            bot.send_document(message.chat.id, csv_file, caption="Ваш результат в формате CSV.")
                    elif answer.startswith("TXT"):
                        txt_filename = "output.txt"
                        with open(txt_filename, "w", encoding="utf-8") as txt_file:
                            txt_file.write(answer)
                        with open(txt_filename, "rb") as txt_file:
                            bot.send_document(message.chat.id, txt_file, caption="Ваш текстовый результат.")
                    else:
                        bot.send_message(message.chat.id, answer)
            else:
                bot.send_message(message.chat.id, "Пожалуйста, сначала загрузите PDF файл.")
        else:
            bot.send_message(message.chat.id, "Пожалуйста, отправьте текстовое сообщение.")
    else:
        bot.send_message(message.chat.id, "Этот тип сообщения не поддерживается. Пожалуйста, отправьте текст или PDF.")


    
bot.polling()
