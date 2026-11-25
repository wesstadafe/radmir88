import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
from config import Config
from database import get_connection, init_db

logging.basicConfig(
    filename=Config.LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)

class WebParser:
    def __init__(self):
        self.is_running = False
        self.stop_requested = False
        self.status = "ожидание"
        self.pages_processed = 0
        self.items_added = 0
        self.items_updated = 0
        self.logs = []

    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}"
        self.logs.append(entry)
        if len(self.logs) > 100:
            self.logs.pop(0)
        if level == "ERROR":
            logging.error(message)
        else:
            logging.info(message)

    def stop(self):
        if self.is_running:
            self.stop_requested = True
            self.log("Получен запрос на остановку парсинга...")

    def fetch_page(self, url):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) IS-ParserDB/1.0"}
        for attempt in range(1, Config.MAX_RETRIES + 1):
            try:
                resp = requests.get(url, headers=headers, timeout=Config.REQUEST_TIMEOUT, proxies={"http": None, "https": None})

                resp.raise_for_status()
                resp.encoding = "utf-8"
                return resp.text
            except Exception as e:
                self.log(f"Попытка {attempt}/{Config.MAX_RETRIES} не удалась для {url}: {e}", "ERROR")
                time.sleep(1)
        return None

    def run(self, base_url, max_pages=3, category_filter=""):
        if self.is_running:
            return
        init_db()
        self.is_running = True
        self.stop_requested = False
        self.status = "выполняется"
        self.pages_processed = 0
        self.items_added = 0
        self.items_updated = 0
        self.logs = []

        started_at = datetime.now().isoformat(timespec="seconds")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO parse_logs (started_at, status) VALUES (?, ?)",
            (started_at, "выполняется")
        )
        log_id = cursor.lastrowid
        conn.commit()

        self.log(f"Старт парсинга. Лимит страниц: {max_pages}")
        error_msg = None

        try:
            for page in range(1, max_pages + 1):
                if self.stop_requested:
                    self.status = "остановлено пользователем"
                    self.log("Парсинг прерван пользователем.")
                    break

                target_url = base_url.format(page=page) if "{page}" in base_url else base_url
                self.log(f"Загрузка страницы {page}: {target_url}")
                html = self.fetch_page(target_url)

                if not html:
                    self.log(f"Пропуск страницы {page} из-за ошибки сети.", "ERROR")
                    continue

                soup = BeautifulSoup(html, "html.parser")
                cards = soup.select("article.product_pod")

                if not cards:
                    self.log("Элементы на странице не найдены. Завершение обхода.")
                    break

                for card in cards:
                    try:
                        title_el = card.select_one("h3 a")
                        price_el = card.select_one("p.price_color")
                        avail_el = card.select_one("p.instock")

                        title = title_el["title"].strip() if title_el else "Без названия"
                        rel_link = title_el["href"] if title_el else ""
                        source_url = urljoin(target_url, rel_link)

                        raw_price = price_el.text.strip() if price_el else "0"
                        clean_price = float("".join(c for c in raw_price if c.isdigit() or c == "."))

                        category = category_filter.strip() if category_filter.strip() else "Книги"
                        description = avail_el.text.strip() if avail_el else "Нет описания"
                        now = datetime.now().isoformat(timespec="seconds")

                        cursor.execute("SELECT id FROM items WHERE source_url = ?", (source_url,))
                        existing = cursor.fetchone()

                        if existing:
                            cursor.execute('''
                                UPDATE items
                                SET title = ?, category = ?, price = ?, description = ?, updated_at = ?
                                WHERE source_url = ?
                            ''', (title, category, clean_price, description, now, source_url))
                            self.items_updated += 1
                        else:
                            cursor.execute('''
                                INSERT INTO items (title, category, price, source_url, description, created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''', (title, category, clean_price, source_url, description, now, now))
                            self.items_added += 1
                    except Exception as item_err:
                        self.log(f"Ошибка разбора карточки: {item_err}", "ERROR")

                conn.commit()
                self.pages_processed += 1
                self.log(f"Страница {page} готова. Добавлено: {self.items_added}, обновлено: {self.items_updated}")

                if "{page}" not in base_url:
                    break

            if not self.stop_requested:
                self.status = "завершено"
                self.log("Парсинг успешно завершён.")

        except Exception as e:
            self.status = "ошибка"
            error_msg = str(e)
            self.log(f"Критическая ошибка парсера: {e}", "ERROR")
        finally:
            finished_at = datetime.now().isoformat(timespec="seconds")
            cursor.execute('''
                UPDATE parse_logs
                SET finished_at = ?, status = ?, pages_processed = ?, items_added = ?, items_updated = ?, error_message = ?
                WHERE id = ?
            ''', (finished_at, self.status, self.pages_processed, self.items_added, self.items_updated, error_msg, log_id))
            conn.commit()
            conn.close()
            self.is_running = False

parser_instance = WebParser()

if __name__ == "__main__":
    parser_instance.run(Config.DEFAULT_TARGET_URL, max_pages=1, category_filter="Книги")
    print(f"Статус: {parser_instance.status} | Добавлено: {parser_instance.items_added} | Обновлено: {parser_instance.items_updated}")
