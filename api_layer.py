import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from query_service import query_items
from parser_module import parser_instance

SAMPLE_CATALOG = {
    1: [
        ("Процессор AMD Ryzen 5 5600 OEM", "11490.00", "В наличии • 6 ядер, 3.5 ГГц, AM4", "/item/ryzen-5-5600"),
        ("Видеокарта Palit GeForce RTX 4060 Dual 8GB", "34990.00", "В наличии • GDDR6, 128 бит", "/item/rtx-4060-dual"),
        ("Материнская плата MSI B550M PRO-VDH", "9890.00", "В наличии • Socket AM4, DDR4", "/item/msi-b550m"),
        ("Оперативная память Kingston FURY Beast 16GB", "4590.00", "В наличии • DDR4, 3200 МГц", "/item/kingston-16gb"),
        ("SSD накопитель Samsung 980 1TB M.2", "8990.00", "В наличии • NVMe PCIe 3.0", "/item/samsung-980-1tb"),
    ],
    2: [
        ("Процессор Intel Core i5-12400F OEM", "13290.00", "В наличии • 6 ядер, LGA 1700", "/item/i5-12400f"),
        ("Видеокарта Sapphire AMD Radeon RX 7600 8GB", "31500.00", "В наличии • GDDR6, 128 бит", "/item/rx-7600"),
        ("Блок питания DEEPCOOL PK650D 650W", "5690.00", "В наличии • 80 PLUS Bronze", "/item/deepcool-650w"),
        ("Кулер для процессора ID-COOLING SE-224-XTS", "2190.00", "В наличии • TDP 220 Вт", "/item/se-224-xts"),
        ("Корпус MONTECH AIR 100 LITE черный", "4990.00", "В наличии • Mini-Tower, закаленное стекло", "/item/montech-air100"),
    ],
    3: [
        ("Монитор 23.8 AOC 24G2SP/BK 165 Гц", "17490.00", "В наличии • IPS, 1920x1080, 1 мс", "/item/aoc-24g2sp"),
        ("Клавиатура механическая Keychron C3 Pro", "5490.00", "В наличии • Red Switch, подсветка", "/item/keychron-c3"),
        ("Мышь беспроводная Logitech G305 LIGHTSPEED", "4290.00", "В наличии • 12000 DPI, 6 кнопок", "/item/logitech-g305"),
        ("Ноутбук ASUS VivoBook 15 X1504ZA", "52990.00", "В наличии • Core i5, 16GB, 512GB SSD", "/item/asus-vivobook15"),
        ("Жесткий диск WD Blue 2TB 7200 rpm", "6490.00", "В наличии • SATA III, кэш 256 МБ", "/item/wd-blue-2tb"),
    ]
}

class InternalAPIHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html_text, status=200):
        body = html_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            if parsed.path == "/api/items":
                try:
                    res = query_items(
                        keyword=params.get("q", [""]),
                        category=params.get("category", [""]),
                        min_price=params.get("min_price", [None]),
                        max_price=params.get("max_price", [None]),
                        sort_by=params.get("sort_by", ["updated_at"]),
                        order=params.get("order", ["DESC"]),
                        page=int(params.get("page", ["1"])),
                        per_page=int(params.get("per_page", ["20"]))
                    )
                    self._send_json(res, 200)
                except ValueError:
                    self._send_json({"error": "Некорректные числовые параметры запроса"}, 400)

            elif parsed.path == "/api/parser/status":
                self._send_json({
                    "is_running": parser_instance.is_running,
                    "status": parser_instance.status,
                    "pages_processed": parser_instance.pages_processed,
                    "items_added": parser_instance.items_added,
                    "items_updated": parser_instance.items_updated
                }, 200)

            elif parsed.path == "/catalog":
                page = int(params.get("page", ["1"])[0])
                items = SAMPLE_CATALOG.get(page, [])
                cards_html = ""
                for title, price, desc, href in items:
                    cards_html += f'<article class="product_pod"><h3><a href="{href}" title="{title}">{title}</a></h3><p class="price_color">{price}</p><p class="instock">{desc}</p></article>'
                self._send_html(f"<html><body>{cards_html}</body></html>", 200)

            elif parsed.path.startswith("/item/"):
                slug = parsed.path.split("/")[-1]
                self._send_html(f"<html><body><h2>Карточка товара: {slug}</h2></body></html>", 200)

            else:
                self._send_json({"error": "Endpoint не найден"}, 404)
        except Exception as e:
            print("ОШИБКА СЕРВЕРА:", repr(e))
            self._send_json({"error": str(e)}, 500)

        pass

def start_background_api(host="127.0.0.1", port=8000):
    server = HTTPServer((host, port), InternalAPIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
