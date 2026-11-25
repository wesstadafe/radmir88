import csv
import io
import json
from database import get_connection

def query_items(keyword="", category="", min_price=None, max_price=None, sort_by="updated_at", order="DESC", page=1, per_page=20):
    allowed_sort = {"title", "price", "updated_at", "created_at", "category"}
    if sort_by not in allowed_sort:
        sort_by = "updated_at"
    order = "ASC" if str(order).upper() == "ASC" else "DESC"

    conditions = []
    params = []

    if keyword:
        conditions.append("(title LIKE ? OR description LIKE ?)")
        like_kw = f"%{keyword.strip()}%"
        params.extend([like_kw, like_kw])

    if category:
        conditions.append("category = ?")
        params.append(category.strip())

    if min_price is not None and str(min_price).strip() != "":
        conditions.append("price >= ?")
        params.append(float(min_price))

    if max_price is not None and str(max_price).strip() != "":
        conditions.append("price <= ?")
        params.append(float(max_price))

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT COUNT(*) as total FROM items {where_clause}", params)
    total = cursor.fetchone()["total"]

    offset = (max(1, int(page)) - 1) * int(per_page)
    sql = f"""
        SELECT id, title, category, price, source_url, description, created_at, updated_at
        FROM items
        {where_clause}
        ORDER BY {sort_by} {order}
        LIMIT ? OFFSET ?
    """
    cursor.execute(sql, params + [int(per_page), offset])
    rows = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT category FROM items WHERE category IS NOT NULL AND category != ''")
    categories = [r["category"] for r in cursor.fetchall()]

    conn.close()
    return {
        "items": rows,
        "total": total,
        "page": int(page),
        "per_page": int(per_page),
        "categories": categories
    }

def export_to_csv(items):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["ID", "Наименование", "Категория", "Цена", "Описание", "URL", "Обновлено"])
    for item in items:
        writer.writerow([
            item["id"], item["title"], item["category"],
            item["price"], item["description"], item["source_url"], item["updated_at"]
        ])
    return output.getvalue().encode("utf-8-sig")

def export_to_json(items):
    return json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8")
