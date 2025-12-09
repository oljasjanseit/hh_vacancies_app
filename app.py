import streamlit as st
import requests
import pandas as pd
import time
import random
from bs4 import BeautifulSoup
import io

st.set_page_config(page_title="HH Full Scraper (fixed)", layout="wide")
st.title("🔥 HH FULL Vacancy Scraper — исправленная версия")

# ---------------------------
# INPUTS
# ---------------------------
title_keywords_input = st.text_area(
    "🔍 Ключевые слова в названии (через запятую):",
    value="продукт менеджер, product manager, продакт менеджер, продуктовый менеджер"
)

title_exclude_input = st.text_area(
    "🚫 Исключить слова в названии (через запятую):",
    value="стажер, intern"
)

desc_keywords_input = st.text_area(
    "📌 Ключевые слова в описании (через запятую):",
    value="Firebase,Amplitude"
)

desc_exclude_input = st.text_area(
    "🚫 Исключить слова в описании (через запятую):",
    value="1C, водитель"
)

desc_mode = st.radio(
    "Как применять ключевые слова в описании?",
    ["Хотя бы одно совпадение", "Все слова должны совпасть"]
)

# normalize lists
title_keywords = [t.strip().lower() for t in title_keywords_input.split(",") if t.strip()]
title_exclude = [t.strip().lower() for t in title_exclude_input.split(",") if t.strip()]
desc_keywords = [t.strip().lower() for t in desc_keywords_input.split(",") if t.strip()]
desc_exclude = [t.strip().lower() for t in desc_exclude_input.split(",") if t.strip()]

# ---------------------------
# helper: fetch whole description with multiple fallbacks
# ---------------------------
def fetch_full_description(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "lxml")

        texts = []

        # 1) стандартный контейнер hh
        c = soup.find("div", {"data-qa": "vacancy-description"})
        if c:
            texts.append(c.get_text(" ", strip=True))

        # 2) альтернативные контейнеры часто встречающиеся
        for cls in ["g-user-content", "vacancy-section", "vacancy-description__text"]:
            alt = soup.find("div", class_=cls)
            if alt:
                texts.append(alt.get_text(" ", strip=True))

        # 3) все <section> или <article> внутри страницы (fallback)
        for tag in soup.find_all(["article", "section"]):
            texts.append(tag.get_text(" ", strip=True))

        # 4) meta description (если есть)
        meta = soup.find("meta", {"name": "description"})
        if meta and meta.get("content"):
            texts.append(meta["content"])

        # 5) последний шанс — весь текст страницы
        if not texts:
            texts.append(soup.get_text(" ", strip=True))

        merged = " ".join([t for t in texts if t]).replace("\n", " ")
        merged = " ".join(merged.split())  # normalize spaces
        return merged.lower()
    except Exception:
        return ""

# ---------------------------
# helper: get pages count for a keyword (single quick request)
# ---------------------------
def get_pages_for_keyword(api_url, keyword, area_id, per_page):
    try:
        params = {"text": keyword, "area": area_id, "per_page": per_page, "page": 0}
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(api_url, params=params, headers=headers, timeout=10)
        if r.status_code != 200:
            return 0, 0  # pages, found
        data = r.json()
        pages = data.get("pages", 0) or 0
        found = data.get("found", 0) or 0
        return pages, found
    except Exception:
        return 0, 0

# ---------------------------
# MAIN SEARCH
# ---------------------------
if st.button("🚀 Запустить поиск"):

    # basic config
    hh_api = "https://api.hh.kz/vacancies"
    per_page = 100
    area_id = 160  # Алматы

    st.info("Подготовка... собираю метаданные по ключевым словам")
    status = st.empty()
    found_counter = st.empty()

    # 1) предварительный проход — узнаем общее число страниц по каждому ключу
    total_pages = 0
    pages_for_key = {}
    found_for_key = {}
    for kw in title_keywords:
        pgs, found = get_pages_for_keyword(hh_api, kw, area_id, per_page)
        # guard: pages may be large; ensure int
        pgs = int(pgs) if isinstance(pgs, (int, float)) else 0
        found = int(found) if isinstance(found, (int, float)) else 0
        pages_for_key[kw] = max(pgs, 1)  # at least 1 to process page0
        found_for_key[kw] = found
        total_pages += pages_for_key[kw]
        time.sleep(random.uniform(0.15, 0.3))  # light throttle

    if total_pages == 0:
        total_pages = 1

    status.info(f"Предварительно определено {total_pages} страниц для обработки.")
    progress = st.progress(0.0)

    # 2) реальный проход, с точным прогрессом
    vacancies = []
    seen_ids = set()
    processed_pages = 0

    for kw in title_keywords:
        max_pages_for_kw = pages_for_key.get(kw, 1)
        current_page = 0

        while current_page < max_pages_for_kw:
            status.write(f"🔎 Ключ: **{kw}** — страница {current_page+1}/{max_pages_for_kw}")
            params = {"text": kw, "area": area_id, "per_page": per_page, "page": current_page}
            headers = {"User-Agent": "Mozilla/5.0"}

            try:
                r = requests.get(hh_api, params=params, headers=headers, timeout=12)
                # handle transient server errors
                if r.status_code in (429, 500, 502, 503, 504):
                    status.warning(f"Сервер ответил {r.status_code}, подождём и попробуем снова")
                    time.sleep(random.uniform(1.0, 2.5))
                    continue
                if r.status_code != 200:
                    status.error(f"Ошибка запроса: {r.status_code} (пропускаю страницу)")
                    break

                data = r.json()
                items = data.get("items", [])
                if not items:
                    # если вдруг API сказал, что pages>0, но items пустые — выйдем с данной страницы
                    break

                for vac in items:
                    # take id and ensure uniqueness
                    vac_id = vac.get("id")
                    if vac_id in seen_ids:
                        continue
                    seen_ids.add(vac_id)

                    title = (vac.get("name") or "").lower()

                    # фильтрация по названию
                    if title_keywords and not any(tok in title for tok in title_keywords):
                        continue
                    if title_exclude and any(ex in title for ex in title_exclude):
                        continue

                    # подгружаем описание и проверяем desc-фильтры
                    url = vac.get("alternate_url") or ""
                    full_desc = fetch_full_description(url)

                    if desc_exclude and any(ex in full_desc for ex in desc_exclude):
                        continue

                    if desc_keywords:
                        if desc_mode == "Хотя бы одно совпадение":
                            if not any(k in full_desc for k in desc_keywords):
                                continue
                        else:
                            if not all(k in full_desc for k in desc_keywords):
                                continue

                    # адрес
                    addr = vac.get("address") or {}
                    street = addr.get("street") or ""
                    building = addr.get("building") or ""
                    address = f"{street} {building}".strip() or "-"

                    # 2GIS link
                    if address != "-":
                        query = f"Алматы, {address}".replace(" ", "+")
                        address_link = f"https://2gis.kz/almaty/search/{query}"
                    else:
                        address_link = "-"

                    vacancies.append({
                        "ID": vac_id,
                        "Название": vac.get("name") or "-",
                        "Компания": (vac.get("employer") or {}).get("name") or "-",
                        "Дата публикации": (vac.get("published_at") or "-")[:10],
                        "Адрес": address,
                        "Ссылка HH": url or "-",
                        "Ссылка 2GIS": address_link
                    })

                # завершили страницу
                current_page += 1
                processed_pages += 1
                # обновляем прогресс (точно по числу страниц)
                progress.progress(min(processed_pages / total_pages, 1.0))
                found_counter.markdown(f"**Найдено вакансий:** {len(vacancies)}")
                # небольшая случайная задержка
                time.sleep(random.uniform(0.2, 0.6))

            except Exception as e:
                status.error(f"Исключение при запросе: {e}. Пропускаю страницу.")
                current_page += 1
                processed_pages += 1
                progress.progress(min(processed_pages / total_pages, 1.0))
                time.sleep(0.5)
                continue

    status.success("Обработка завершена.")

    st.write(f"Всего найдено вакансий: **{len(vacancies)}**")

    # ---------------------------
    # OUTPUT
    # ---------------------------
    if vacancies:
        df = pd.DataFrame(vacancies)

        # создаём кликабельные HTML ссылки (для отображения в таблице)
        df_display = df.copy()
        df_display["Ссылка HH"] = df_display["Ссылка HH"].apply(
            lambda x: f'<a href="{x}" target="_blank">🔗 Открыть HH</a>' if x and x != "-" else "-"
        )
        df_display["Ссылка 2GIS"] = df_display["Ссылка 2GIS"].apply(
            lambda x: f'<a href="{x}" target="_blank">📍 2GIS</a>' if x and x != "-" else "-"
        )

        # корректная HTML-таблица со стилями (заголовок НЕ белый)
        table_html = df_display.to_html(escape=False, index=False)
        styled = f"""
        <style>
         thead th {{ background:#1f2937; color:#fff; padding:8px; position: sticky; top:0; z-index:1; }}
         table {{ border-collapse: collapse; width:100%; font-family: Arial, sans-serif; }}
         td, th {{ border: 1px solid #ddd; padding: 8px; text-align:left; vertical-align: top; }}
         tbody tr:nth-child(odd){{ background:#fbfbfb; }}
         tbody tr:hover{{ background:#eef6ff; }}
         a {{ text-decoration:none; color: #0645AD; font-weight:600; }}
        </style>
        {table_html}
        """

        st.markdown(styled, unsafe_allow_html=True)

        # Excel (чистые значения без HTML)
        excel_buffer = io.BytesIO()
        pd.DataFrame(vacancies).to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        st.download_button(
            label="⬇ Скачать Excel",
            data=excel_buffer,
            file_name="vacancies.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("По заданным фильтрам вакансий не найдено.")
