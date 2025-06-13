import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import pickle
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import configparser
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import re
from datetime import datetime
import collections

# Глобальные переменные для хранения данных
reviewers = {}
products = {}
reviews = {}

# Глобальные переменные для интерфейса
root = None
notebook = None
reviewers_tree = None
products_tree = None
reviews_tree = None
plot_frame = None

# Переменные конфигурации
config = None
data_dir = None

# Список стоп-слов для английского языка
STOP_WORDS = {"i", "you", "my", "your","a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he", "in",
              "of", "on", "that", "the", "to", "was", "were", "will", "with", "this", "these", "those", "am", "been",
              "being", "have", "had", "having", "do", "does", "did", "but", "if", "or", "because", "as", "until",
              "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during",
              "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over",
              "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any",
              "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same",
              "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now", "is", "it", "its"}


# Загрузка конфигурации из файла config.ini
def load_config():
    global config, data_dir

    config = configparser.ConfigParser()

    # Значения по умолчанию
    config.read_dict({
        'DATABASE': {
            'data_directory': 'data',
            'reviewers_file': 'reviewers.pkl',
            'products_file': 'products.pkl',
            'reviews_file': 'reviews.pkl'
        },
        'INTERFACE': {
            'window_title': 'Анализатор отзывов',
            'window_width': '1200',
            'window_height': '800',
            'max_reviews_display': '100'
        },
        'ANALYSIS': {
            'top_products_count': '10',
            'top_reviewers_count': '10',
            'histogram_bins': '5',
            'chart_colors': 'skyblue,lightgreen,orange'
        },
        'FILES': {
            'jsonl_extension': '*.json',
            'supported_encodings': 'utf-8,cp1251,latin1'
        },
        'APPEARANCE': {
            'tab_padding_x': '10',
            'tab_padding_y': '10',
            'button_padding': '5',
            'table_column_width': '150'
        }
    })

    # Чтение файла конфигурации
    try:
        config.read('config.ini', encoding='utf-8')
    except Exception as e:
        print(f"Ошибка чтения config.ini: {e}")
        print("Используются настройки по умолчанию")

    # Создание каталога для данных
    data_dir = Path(config.get('DATABASE', 'data_directory'))
    data_dir.mkdir(parents=True, exist_ok=True)


# Создание главного окна приложения
def create_main_window():
    global root

    root = tk.Tk()
    root.title(config.get('INTERFACE', 'window_title'))

    width = config.getint('INTERFACE', 'window_width')
    height = config.getint('INTERFACE', 'window_height')
    root.geometry(f"{width}x{height}")


# Создание графического интерфейса
def setup_ui():
    global notebook

    # Создание вкладок
    pad_x = config.getint('APPEARANCE', 'tab_padding_x')
    pad_y = config.getint('APPEARANCE', 'tab_padding_y')

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=pad_x, pady=pad_y)

    # Создание вкладок
    reviewers_frame = ttk.Frame(notebook)
    notebook.add(reviewers_frame, text="Рецензенты")
    setup_reviewers_tab(reviewers_frame)

    products_frame = ttk.Frame(notebook)
    notebook.add(products_frame, text="Продукты")
    setup_products_tab(products_frame)

    reviews_frame = ttk.Frame(notebook)
    notebook.add(reviews_frame, text="Отзывы")
    setup_reviews_tab(reviews_frame)

    analysis_frame = ttk.Frame(notebook)
    notebook.add(analysis_frame, text="Анализ")
    setup_analysis_tab(analysis_frame)


# Интерфейс управления справочником рецензентов
def setup_reviewers_tab(parent_frame):
    global reviewers_tree

    # Таблица рецензентов
    columns = ('ID', 'Имя', 'Всего отзывов', 'Средняя оценка')
    reviewers_tree = ttk.Treeview(parent_frame, columns=columns, show='headings')

    col_width = config.getint('APPEARANCE', 'table_column_width')
    for col in columns:
        reviewers_tree.heading(col, text=col)
        reviewers_tree.column(col, width=col_width)

    reviewers_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

    # Кнопки управления
    btn_frame = ttk.Frame(parent_frame)
    btn_frame.pack(fill=tk.X)

    btn_padding = config.getint('APPEARANCE', 'button_padding')

    ttk.Button(btn_frame, text="Добавить", command=add_reviewer).pack(side=tk.LEFT, padx=btn_padding)
    ttk.Button(btn_frame, text="Удалить", command=delete_reviewer).pack(side=tk.LEFT, padx=btn_padding)
    ttk.Button(btn_frame, text="Загрузить из JSONL", command=load_jsonl).pack(side=tk.LEFT, padx=btn_padding)
    ttk.Button(btn_frame, text="Сохранить", command=save_data).pack(side=tk.RIGHT, padx=btn_padding)


# Интерфейс управления справочником продуктов
def setup_products_tab(parent_frame):
    global products_tree

    columns = ('ASIN', 'Название', 'Категория', 'Всего отзывов', 'Средняя оценка')
    products_tree = ttk.Treeview(parent_frame, columns=columns, show='headings')

    col_width = config.getint('APPEARANCE', 'table_column_width')
    for col in columns:
        products_tree.heading(col, text=col)
        products_tree.column(col, width=col_width)

    products_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

    btn_frame = ttk.Frame(parent_frame)
    btn_frame.pack(fill=tk.X)

    btn_padding = config.getint('APPEARANCE', 'button_padding')

    ttk.Button(btn_frame, text="Добавить", command=add_product).pack(side=tk.LEFT, padx=btn_padding)
    ttk.Button(btn_frame, text="Удалить", command=delete_product).pack(side=tk.LEFT, padx=btn_padding)


# Интерфейс управления отзывами
def setup_reviews_tab(parent_frame):
    global reviews_tree

    columns = ('ID', 'Рецензент', 'Продукт', 'Оценка', 'Дата', 'Краткое содержание')
    reviews_tree = ttk.Treeview(parent_frame, columns=columns, show='headings')

    for col in columns:
        reviews_tree.heading(col, text=col)
        reviews_tree.column(col, width=120)

    reviews_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

    btn_frame = ttk.Frame(parent_frame)
    btn_frame.pack(fill=tk.X)

    btn_padding = config.getint('APPEARANCE', 'button_padding')

    ttk.Button(btn_frame, text="Добавить", command=add_review).pack(side=tk.LEFT, padx=btn_padding)
    ttk.Button(btn_frame, text="Удалить", command=delete_review).pack(side=tk.LEFT, padx=btn_padding)


#Интерфейс анализа данных
def setup_analysis_tab(parent_frame):
    global plot_frame

    control_frame = ttk.Frame(parent_frame)
    control_frame.pack(fill=tk.X, pady=(0, 10))

    btn_padding = config.getint('APPEARANCE', 'button_padding')

    ttk.Button(control_frame, text="Анализ рейтингов", command=analyze_ratings).pack(side=tk.LEFT, padx=btn_padding)
    ttk.Button(control_frame, text="Топ продукты", command=analyze_top_products).pack(side=tk.LEFT, padx=btn_padding)
    ttk.Button(control_frame, text="Удовлетворенность клиентов", command=analyze_customer_satisfaction).pack(side=tk.LEFT, padx=btn_padding)

    # Область для графиков
    plot_frame = ttk.Frame(parent_frame)
    plot_frame.pack(fill=tk.BOTH, expand=True)

# Загрузка данных из файлов
def load_data():
    global reviewers, products, reviews

    try:
        reviewers_file = data_dir / config.get('DATABASE', 'reviewers_file')
        products_file = data_dir / config.get('DATABASE', 'products_file')
        reviews_file = data_dir / config.get('DATABASE', 'reviews_file')

        if reviewers_file.exists():
            with open(reviewers_file, 'rb') as f:
                reviewers = pickle.load(f)

        if products_file.exists():
            with open(products_file, 'rb') as f:
                products = pickle.load(f)

        if reviews_file.exists():
            with open(reviews_file, 'rb') as f:
                reviews = pickle.load(f)

        refresh_tables()
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка загрузки данных: {e}")


#Сохранение данных в двоичном формате
def save_data():
    try:
        reviewers_file = data_dir / config.get('DATABASE', 'reviewers_file')
        products_file = data_dir / config.get('DATABASE', 'products_file')
        reviews_file = data_dir / config.get('DATABASE', 'reviews_file')

        with open(reviewers_file, 'wb') as f:
            pickle.dump(reviewers, f)

        with open(products_file, 'wb') as f:
            pickle.dump(products, f)

        with open(reviews_file, 'wb') as f:
            pickle.dump(reviews, f)

        messagebox.showinfo("Успех", "Данные сохранены")
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка сохранения: {e}")


#Загрузка данных из JSONL файла
def load_jsonl():
    jsonl_ext = config.get('FILES', 'jsonl_extension')
    file_path = filedialog.askopenfilename(filetypes=[("JSONL files", jsonl_ext)])
    if not file_path:
        return

    encodings = config.get('FILES', 'supported_encodings').split(',')

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding.strip()) as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip():
                        review_data = json.loads(line)
                        process_review_data(review_data)
                        if line_num % 1000 == 0:
                            root.update_idletasks()

            refresh_tables()
            messagebox.showinfo("Успех", f"Загружено записей: {len(reviews)}")
            return
        except (UnicodeDecodeError, UnicodeError):
            continue
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка загрузки JSONL: {e}")
            return

    messagebox.showerror("Ошибка", "Не удалось определить кодировку файла")


# Обработка данных отзыва в нормализованную структуру
def process_review_data(data):
    global reviewers, products, reviews

    reviewer_id = data.get('reviewerID', '')
    asin = data.get('asin', '')

    # Добавление в справочник рецензентов
    if reviewer_id and reviewer_id not in reviewers:
        reviewers[reviewer_id] = {
            'name': data.get('reviewerName', 'Неизвестно'),
            'total_reviews': 0,
            'total_rating': 0
        }

    # Добавление в справочник продуктов
    if asin and asin not in products:
        products[asin] = {
            'name': f"Продукт {asin}",
            'category': 'Видеоигры',
            'total_reviews': 0,
            'total_rating': 0
        }

    # Добавление отзыва
    review_id = len(reviews) + 1
    rating = float(data.get('overall', 0))

    reviews[review_id] = {
        'reviewer_id': reviewer_id,
        'asin': asin,
        'rating': rating,
        'date': data.get('reviewTime', ''),
        'summary': data.get('summary', '')[:50] + '...' if len(data.get('summary', '')) > 50 else data.get('summary', ''),
        'text': data.get('reviewText', '')
    }

    # Обновление статистики
    if reviewer_id in reviewers:
        reviewers[reviewer_id]['total_reviews'] += 1
        reviewers[reviewer_id]['total_rating'] += rating

    if asin in products:
        products[asin]['total_reviews'] += 1
        products[asin]['total_rating'] += rating


# Обновление таблиц
def refresh_tables():

    # Обновление таблицы рецензентов
    for item in reviewers_tree.get_children():
        reviewers_tree.delete(item)

    for reviewer_id, data in reviewers.items():
        avg_rating = round(data['total_rating'] / data['total_reviews'], 2) if data['total_reviews'] > 0 else 0
        reviewers_tree.insert('', 'end', values=(
            reviewer_id, data['name'], data['total_reviews'], avg_rating
        ))

    # Обновление таблицы продуктов
    for item in products_tree.get_children():
        products_tree.delete(item)

    for asin, data in products.items():
        avg_rating = round(data['total_rating'] / data['total_reviews'], 2) if data['total_reviews'] > 0 else 0
        products_tree.insert('', 'end', values=(
            asin, data['name'], data['category'], data['total_reviews'], avg_rating
        ))

    # Обновление таблицы отзывов
    for item in reviews_tree.get_children():
        reviews_tree.delete(item)

    max_display = config.getint('INTERFACE', 'max_reviews_display')
    for review_id, data in list(reviews.items())[-max_display:]:
        reviewer_name = reviewers.get(data['reviewer_id'], {}).get('name', 'Неизвестно')
        product_name = products.get(data['asin'], {}).get('name', 'Неизвестно')
        reviews_tree.insert('', 'end', values=(
            review_id, reviewer_name, product_name, data['rating'], data['date'], data['summary']
        ))


# Добавление нового рецензента
def add_reviewer():

    dialog = tk.Toplevel(root)
    dialog.title("Добавить рецензента")
    dialog.geometry("300x150")

    tk.Label(dialog, text="ID:").pack()
    id_entry = tk.Entry(dialog)
    id_entry.pack()

    tk.Label(dialog, text="Имя:").pack()
    name_entry = tk.Entry(dialog)
    name_entry.pack()

    def save():
        reviewer_id = id_entry.get()
        name = name_entry.get()
        if reviewer_id and name:
            reviewers[reviewer_id] = {'name': name, 'total_reviews': 0, 'total_rating': 0}
            refresh_tables()
            dialog.destroy()

    tk.Button(dialog, text="Сохранить", command=save).pack(pady=10)

# Удаление рецензента
def delete_reviewer():

    selection = reviewers_tree.selection()
    if selection:
        item = reviewers_tree.item(selection[0])
        reviewer_id = item['values'][0]
        del reviewers[reviewer_id]
        refresh_tables()


# Добавление нового продукта
def add_product():

    dialog = tk.Toplevel(root)
    dialog.title("Добавить продукт")
    dialog.geometry("300x200")

    tk.Label(dialog, text="ASIN:").pack()
    asin_entry = tk.Entry(dialog)
    asin_entry.pack()

    tk.Label(dialog, text="Название:").pack()
    name_entry = tk.Entry(dialog)
    name_entry.pack()

    tk.Label(dialog, text="Категория:").pack()
    category_entry = tk.Entry(dialog)
    category_entry.pack()

    def save():
        asin = asin_entry.get()
        name = name_entry.get()
        category = category_entry.get()
        if asin and name:
            products[asin] = {'name': name, 'category': category, 'total_reviews': 0, 'total_rating': 0}
            refresh_tables()
            dialog.destroy()

    tk.Button(dialog, text="Сохранить", command=save).pack(pady=10)


# даление продукта
def delete_product():

    selection = products_tree.selection()
    if selection:
        item = products_tree.item(selection[0])
        asin = item['values'][0]
        del products[asin]
        refresh_tables()


# Добавление нового отзыва
def add_review():
    if not reviewers or not products:
        messagebox.showwarning("Предупреждение", "Сначала добавьте рецензентов и продукты")
        return

    dialog = tk.Toplevel(root)
    dialog.title("Добавить отзыв")
    dialog.geometry("400x300")

    tk.Label(dialog, text="Рецензент:").pack()
    reviewer_var = tk.StringVar()
    reviewer_combo = ttk.Combobox(dialog, textvariable=reviewer_var, values=list(reviewers.keys()))
    reviewer_combo.pack()

    tk.Label(dialog, text="Продукт:").pack()
    product_var = tk.StringVar()
    product_combo = ttk.Combobox(dialog, textvariable=product_var, values=list(products.keys()))
    product_combo.pack()

    tk.Label(dialog, text="Оценка (1-5):").pack()
    rating_entry = tk.Entry(dialog)
    rating_entry.pack()

    tk.Label(dialog, text="Краткое содержание:").pack()
    summary_entry = tk.Entry(dialog)
    summary_entry.pack()

    def save():
        try:
            reviewer_id = reviewer_var.get()
            asin = product_var.get()
            rating = float(rating_entry.get())
            summary = summary_entry.get()

            if reviewer_id and asin and 1 <= rating <= 5:
                review_id = len(reviews) + 1
                reviews[review_id] = {
                    'reviewer_id': reviewer_id,
                    'asin': asin,
                    'rating': rating,
                    'date': datetime.now().strftime("%m %d, %Y"),
                    'summary': summary,
                    'text': ''
                }

                # Обновление статистики
                reviewers[reviewer_id]['total_reviews'] += 1
                reviewers[reviewer_id]['total_rating'] += rating
                products[asin]['total_reviews'] += 1
                products[asin]['total_rating'] += rating

                refresh_tables()
                dialog.destroy()
            else:
                messagebox.showerror("Ошибка", "Проверьте введенные данные")
        except ValueError:
            messagebox.showerror("Ошибка", "Неверный формат оценки")

    tk.Button(dialog, text="Сохранить", command=save).pack(pady=10)


# Удаление отзыва
def delete_review():

    selection = reviews_tree.selection()
    if selection:
        item = reviews_tree.item(selection[0])
        review_id = item['values'][0]
        del reviews[review_id]
        refresh_tables()


# Анализ распределения рейтингов
def analyze_ratings():

    try:
        if not reviews:
            messagebox.showwarning("Предупреждение", "Нет данных для анализа")
            return

        ratings = [review['rating'] for review in reviews.values()]

        # Очистка предыдущих графиков
        for widget in plot_frame.winfo_children():
            widget.destroy()

        bins = config.getint('ANALYSIS', 'histogram_bins')
        colors = config.get('ANALYSIS', 'chart_colors').split(',')

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(ratings, bins=bins, range=(1, 6), alpha=0.7, color=colors[0].strip(), edgecolor='black')
        ax.set_xlabel('Рейтинг')
        ax.set_ylabel('Количество отзывов')
        ax.set_title('Распределение рейтингов')
        ax.set_xticks([1, 2, 3, 4, 5])

        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw()
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка в analyze_ratings: {e}")


# Анализ топ продуктов
def analyze_top_products():


    try:
        if not products:
            return

        top_count = config.getint('ANALYSIS', 'top_products_count')
        colors = config.get('ANALYSIS', 'chart_colors').split(',')

        # Сортировка продуктов по количеству отзывов
        sorted_products = sorted(products.items(),
                                 key=lambda x: x[1]['total_reviews'], reverse=True)[:top_count]

        names = [f"{asin[:8]}..." for asin, _ in sorted_products]
        counts = [data['total_reviews'] for _, data in sorted_products]

        for widget in plot_frame.winfo_children():
            widget.destroy()

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(names, counts, color=colors[1].strip())
        ax.set_xlabel('Продукты')
        ax.set_ylabel('Количество отзывов')
        ax.set_title(f'Топ-{top_count} продуктов по количеству отзывов')
        plt.xticks(rotation=45)
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw()
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка в analyze_top_products: {e}")


# Анализ самых частых слов в положительных отзывах и построение гистограммы
def analyze_customer_satisfaction():

    try:
        if not reviews:
            messagebox.showwarning("Предупреждение", "Нет данных для анализа")
            return

        # Сбор текста из положительных отзывов (рейтинг > 3)
        positive_reviews_text = " ".join([review['text'].lower() for review in reviews.values() if review['rating'] > 3])

        # Удаление знаков препинания и разбиение на слова
        words = re.findall(r'\b\w+\b', positive_reviews_text)

        # Фильтрация стоп-слов
        filtered_words = [word for word in words if word not in STOP_WORDS]

        # Подсчет частоты слов
        word_counts = collections.Counter(filtered_words)

        # Выбор топ-10 самых частых слов
        top_words = word_counts.most_common(10)
        words, counts = zip(*top_words) if top_words else ([], [])

        # Очистка предыдущих графиков
        for widget in plot_frame.winfo_children():
            widget.destroy()

        if not words:
            messagebox.showinfo("Информация", "Нет данных для отображения")
            return

        # Создание гистограммы
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(words, counts, color='green')
        ax.set_xlabel('Words')
        ax.set_ylabel('Frequency')
        ax.set_title('Top-10 Words in Positive Reviews')
        plt.xticks(rotation=45)
        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        canvas.draw()

    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка в analyze_customer_satisfaction: {e}")


def main():

    # Загрузка конфигурации
    load_config()

    # Создание интерфейса
    create_main_window()
    setup_ui()

    # Загрузка данных
    load_data()

    # Запуск основного цикла
    root.mainloop()


if __name__ == "__main__":
    main()