import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from database import init_db, get_connection
from parser_module import parser_instance
from query_service import query_items, export_to_csv, export_to_json
from api_layer import start_background_api


class ParserDBDesktopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ИС «Парсер-БД» — Сбор, хранение и выдача веб-данных (Windows ПК)")
        self.geometry("1100x680")
        self.minsize(950, 600)

        init_db()
        start_background_api()

        self.current_items = []
        self.current_page = 1
        self.per_page = 20

        self._build_ui()
        self.refresh_search()
        self.refresh_history_table()
        self._poll_parser_status()

    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_search = ttk.Frame(notebook)
        notebook.add(self.tab_search, text="🔍 Поиск и выдача данных (Модуль 6)")
        self._build_search_tab(self.tab_search)

        self.tab_parser = ttk.Frame(notebook)
        notebook.add(self.tab_parser, text="⚙ Управление парсером (Модуль 2)")
        self._build_parser_tab(self.tab_parser)

    def _build_search_tab(self, parent):
        ff = ttk.LabelFrame(parent, text="Параметры запроса к базе данных", padding=10)
        ff.pack(fill="x", padx=10, pady=8)

        ttk.Label(ff, text="Ключевое слово:").grid(row=0, column=0, sticky="w", padx=4)
        self.entry_kw = ttk.Entry(ff, width=28)
        self.entry_kw.grid(row=0, column=1, padx=4)
        self.entry_kw.bind("<Return>", lambda e: self.on_search_click())

        ttk.Label(ff, text="Категория:").grid(row=0, column=2, sticky="w", padx=4)
        self.combo_cat = ttk.Combobox(ff, width=18, state="readonly")
        self.combo_cat.grid(row=0, column=3, padx=4)

        ttk.Label(ff, text="Цена от:").grid(row=0, column=4, sticky="w", padx=4)
        self.entry_min = ttk.Entry(ff, width=9)
        self.entry_min.grid(row=0, column=5, padx=4)

        ttk.Label(ff, text="до:").grid(row=0, column=6, sticky="w", padx=4)
        self.entry_max = ttk.Entry(ff, width=9)
        self.entry_max.grid(row=0, column=7, padx=4)

        ttk.Label(ff, text="Сортировка:").grid(row=1, column=0, sticky="w", padx=4, pady=6)
        self.combo_sort = ttk.Combobox(
            ff, width=16, state="readonly",
            values=["По дате обновления", "По цене", "По названию"]
        )
        self.combo_sort.current(0)
        self.combo_sort.grid(row=1, column=1, sticky="w", padx=4, pady=6)

        self.combo_order = ttk.Combobox(
            ff, width=14, state="readonly",
            values=["По убыванию", "По возрастанию"]
        )
        self.combo_order.current(0)
        self.combo_order.grid(row=1, column=2, columnspan=2, sticky="w", padx=4, pady=6)

        ttk.Button(ff, text="🔍 Найти", command=self.on_search_click).grid(
            row=1, column=4, columnspan=2, padx=4, pady=6, sticky="ew"
        )
        ttk.Button(ff, text="Сбросить", command=self.reset_filters).grid(
            row=1, column=6, columnspan=2, padx=4, pady=6, sticky="ew"
        )

        af = ttk.Frame(parent)
        af.pack(fill="x", padx=10, pady=2)
        self.lbl_total = ttk.Label(af, text="Найдено записей: 0", font=("Segoe UI", 10, "bold"))
        self.lbl_total.pack(side="left")
        ttk.Button(af, text="💾 Экспорт в JSON", command=lambda: self.export_file("json")).pack(side="right", padx=4)
        ttk.Button(af, text="📊 Экспорт в CSV", command=lambda: self.export_file("csv")).pack(side="right", padx=4)

        tf = ttk.Frame(parent)
        tf.pack(fill="both", expand=True, padx=10, pady=6)
        cols = ("id", "title", "category", "price", "description", "updated_at", "url")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings")

        headers = [
            ("id", "ID", 45),
            ("title", "Наименование", 270),
            ("category", "Категория", 110),
            ("price", "Цена (руб.)", 90),
            ("description", "Характеристики / Статус", 180),
            ("updated_at", "Обновлено", 135),
            ("url", "URL источника", 200),
        ]
        for col, title, width in headers:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width)

        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self.open_selected_url)

        pf = ttk.Frame(parent)
        pf.pack(fill="x", padx=10, pady=6)
        ttk.Button(pf, text="← Назад", command=self.prev_page).pack(side="left")
        self.lbl_page = ttk.Label(pf, text="Страница: 1")
        self.lbl_page.pack(side="left", padx=12)
        ttk.Button(pf, text="Вперёд →", command=self.next_page).pack(side="left")
        ttk.Label(
            pf,
            text="Подсказка: двойной клик по строке открывает источник в браузере",
            foreground="gray"
        ).pack(side="right")

    def on_search_click(self):
        self.current_page = 1
        self.refresh_search()

    def reset_filters(self):
        self.entry_kw.delete(0, tk.END)
        self.combo_cat.set("Все категории")
        self.entry_min.delete(0, tk.END)
        self.entry_max.delete(0, tk.END)
        self.combo_sort.current(0)
        self.combo_order.current(0)
        self.current_page = 1
        self.refresh_search()

    def refresh_search(self):
        sort_map = {"По дате обновления": "updated_at", "По цене": "price", "По названию": "title"}
        order_map = {"По убыванию": "DESC", "По возрастанию": "ASC"}
        cat = "" if self.combo_cat.get() == "Все категории" else self.combo_cat.get()

        try:
            res = query_items(
                keyword=self.entry_kw.get(),
                category=cat,
                min_price=self.entry_min.get().strip() or None,
                max_price=self.entry_max.get().strip() or None,
                sort_by=sort_map.get(self.combo_sort.get(), "updated_at"),
                order=order_map.get(self.combo_order.get(), "DESC"),
                page=self.current_page,
                per_page=self.per_page,
            )
        except ValueError:
            messagebox.showerror("Ошибка валидации", "Поля цены должны содержать числа.")
            return

        self.combo_cat["values"] = ["Все категории"] + res["categories"]
        if not self.combo_cat.get():
            self.combo_cat.current(0)

        self.current_items = res["items"]
        self.tree.delete(*self.tree.get_children())

        if not self.current_items:
            self.lbl_total.config(text="По вашему запросу ничего не найдено (0 записей)")
        else:
            self.lbl_total.config(text=f"Найдено записей: {res['total']}")
            for item in self.current_items:
                self.tree.insert("", tk.END, values=(
                    item["id"],
                    item["title"],
                    item["category"],
                    f"{item['price']:.2f}",
                    item["description"],
                    item["updated_at"],
                    item["source_url"],
                ))

        self.lbl_page.config(text=f"Страница: {self.current_page}")

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_search()

    def next_page(self):
        if len(self.current_items) == self.per_page:
            self.current_page += 1
            self.refresh_search()

    def open_selected_url(self, event):
        sel = self.tree.selection()
        if sel:
            url = self.tree.item(sel)["values"]
            if str(url).startswith("http"):
                webbrowser.open(url)

    def export_file(self, fmt):
        cat = "" if self.combo_cat.get() == "Все категории" else self.combo_cat.get()
        res = query_items(
            keyword=self.entry_kw.get(),
            category=cat,
            min_price=self.entry_min.get().strip() or None,
            max_price=self.entry_max.get().strip() or None,
            page=1,
            per_page=50000,
        )
        if not res["items"]:
            messagebox.showwarning("Экспорт", "Нет данных для выгрузки.")
            return

        ext = ".csv" if fmt == "csv" else ".json"
        fp = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(f"{fmt.upper()} файлы", f"*{ext}")],
            initialfile=f"export_items{ext}",
        )
        if not fp:
            return

        data = export_to_csv(res["items"]) if fmt == "csv" else export_to_json(res["items"])
        with open(fp, "wb") as f:
            f.write(data)
        messagebox.showinfo("Успех", f"Выгружено записей: {len(res['items'])}")

    def _build_parser_tab(self, parent):
        cf = ttk.LabelFrame(parent, text="Настройка параметров запуска парсера", padding=10)
        cf.pack(fill="x", padx=10, pady=8)

        ttk.Label(cf, text="Целевой URL ({page} — номер страницы):").grid(row=0, column=0, sticky="w", padx=4)
        self.entry_url = ttk.Entry(cf, width=65)
        self.entry_url.insert(0, "http://127.0.0.1:8000/catalog?page={page}")


        self.entry_url.grid(row=0, column=1, columnspan=3, sticky="we", padx=4)

        ttk.Label(cf, text="Категория:").grid(row=1, column=0, sticky="w", padx=4, pady=6)
        self.entry_parse_cat = ttk.Entry(cf, width=25)
        self.entry_parse_cat.insert(0, "Комплектующие ПК")
        self.entry_parse_cat.grid(row=1, column=1, sticky="w", padx=4, pady=6)

        ttk.Label(cf, text="Глубина (страниц):").grid(row=1, column=2, sticky="e", padx=4, pady=6)
        self.spin_pages = ttk.Spinbox(cf, from_=1, to=50, width=8)
        self.spin_pages.set(3)
        self.spin_pages.grid(row=1, column=3, sticky="w", padx=4, pady=6)

        bf = ttk.Frame(cf)
        bf.grid(row=2, column=0, columnspan=4, sticky="w", pady=4)
        ttk.Button(bf, text="▶ Запустить парсинг", command=self.start_parser).pack(side="left", padx=4)
        ttk.Button(bf, text="⏹ Остановить парсинг", command=self.stop_parser).pack(side="left", padx=4)

        self.lbl_parser_stat = ttk.Label(
            parent,
            text="Статус: ожидание | Страниц: 0 | Добавлено: 0 | Обновлено: 0",
            font=("Segoe UI", 10, "bold"),
        )
        self.lbl_parser_stat.pack(fill="x", padx=12, pady=4)

        lf = ttk.LabelFrame(parent, text="Логи выполнения в реальном времени", padding=6)
        lf.pack(fill="both", expand=True, padx=10, pady=4)
        self.txt_logs = tk.Text(lf, height=10, bg="#1e1e1e", fg="#00ff66", font=("Consolas", 10), state="disabled")
        self.txt_logs.pack(fill="both", expand=True)

        hf = ttk.LabelFrame(parent, text="Журнал запусков парсера (таблица parse_logs)", padding=6)
        hf.pack(fill="both", expand=True, padx=10, pady=6)
        cols = ("id", "started", "finished", "status", "pages", "added", "updated")
        self.hist_tree = ttk.Treeview(hf, columns=cols, show="headings", height=5)

        log_headers = [
            ("id", "ID", 45),
            ("started", "Начало", 150),
            ("finished", "Окончание", 150),
            ("status", "Статус", 180),
            ("pages", "Страниц", 80),
            ("added", "Добавлено", 90),
            ("updated", "Обновлено", 90),
        ]
        for col, title, width in log_headers:
            self.hist_tree.heading(col, text=title)
            self.hist_tree.column(col, width=width)
        self.hist_tree.pack(fill="both", expand=True)

    def start_parser(self):
        url = self.entry_url.get().strip()
        cat = self.entry_parse_cat.get().strip()
        if not url.startswith(("http://", "https://")):
            messagebox.showerror("Ошибка валидации", "URL должен начинаться с http:// или https://")
            return
        try:
            mp = int(self.spin_pages.get())
            if not (1 <= mp <= 50):
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка валидации", "Глубина должна быть от 1 до 50.")
            return

        if parser_instance.is_running:
            messagebox.showwarning("Внимание", "Парсер уже запущен.")
            return

        threading.Thread(target=self._run_parser_worker, args=(url, mp, cat), daemon=True).start()

    def _run_parser_worker(self, url, mp, cat):
        parser_instance.run(url, mp, cat)
        self.after(0, self.refresh_history_table)
        self.after(0, self.refresh_search)

    def stop_parser(self):
        if parser_instance.is_running:
            parser_instance.stop()
        else:
            messagebox.showinfo("Информация", "Парсер сейчас не запущен.")

    def refresh_history_table(self):
        conn = get_connection()
        rows = conn.execute("SELECT * FROM parse_logs ORDER BY id DESC LIMIT 10").fetchall()
        conn.close()
        self.hist_tree.delete(*self.hist_tree.get_children())
        for r in rows:
            self.hist_tree.insert("", tk.END, values=(
                r["id"],
                r["started_at"],
                r["finished_at"] or "-",
                r["status"],
                r["pages_processed"],
                r["items_added"],
                r["items_updated"],
            ))

    def _poll_parser_status(self):
        self.lbl_parser_stat.config(
            text=f"Статус: {parser_instance.status} | "
                 f"Страниц: {parser_instance.pages_processed} | "
                 f"Добавлено: {parser_instance.items_added} | "
                 f"Обновлено: {parser_instance.items_updated}"
        )
        self.txt_logs.config(state="normal")
        self.txt_logs.delete("1.0", tk.END)
        self.txt_logs.insert(tk.END, "\n".join(parser_instance.logs))
        self.txt_logs.see(tk.END)
        self.txt_logs.config(state="disabled")
        self.after(800, self._poll_parser_status)


if __name__ == "__main__":
    app = ParserDBDesktopApp()
    app.mainloop()
