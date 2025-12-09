import streamlit as st
import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
import io

st.set_page_config(page_title="HH Full Scraper", layout="wide")
st.title("🔥 HH FULL Vacancy Scraper — улучшенный интерфейс + прогресс")

# ---------------------------
# INPUTS
# ---------------------------
title_keywords_input = st.text_area(
    "🔍 Ключевые слова в названии:",
    value="продукт менеджер, product manager, продакт менеджер, продуктовый менеджер"
)

title_exclude_input = st.text_area(
    "🚫 Исключить слова в названии:",
    value="стажер, intern"
)

desc_keywords_input = st.text_area(
    "📌 Ключевые слова в описании:",
    value="Firebase,Amplitude"
)

desc_exclude_input = st.text_area(
    "🚫 Исключить слова в описании:",
    value="1C, водитель"
)

desc_mode = st.radio(
    "Как искать ключевые слова в описании?",
    ["Хотя бы одно совпадение", "Все слова должны совпасть"]
)

# Преобразование списков
title_keywords = [t.strip().lower() for t in title_keywords_input.split(",") if t.strip()]
title_exclude = [t.strip().lower() for t in title_exclude_input.split(",") if t.strip()]
desc_keywords = [t.strip().lower() for t in desc_keywords_input.split(",") if t.strip()]
desc_exclude = [t.strip().lower() for t in desc_exclude_input.split(",") if t.strip()]

# ---------------------------
# HTML описания
# ---------------------------
def fetch_full_description(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        html = requests.get(url, headers=headers, timeout=10)

        if html.status_code != 200:
            return ""

        soup = BeautifulSoup(html.text, "lxml")
        block = soup.find("div", {"data-qa": "vacancy-description"})
        if not block:
            return ""

        text = block.get_text(separator=" ", strip=True)
        text = " ".join(text.split())
        return text.lower()

    except:
        return ""


# ---------------------------
# RUN SEARCH
# ---------------------------
if st.button("🚀 Запустить поиск"):

    st.info("🔄 Поиск начался...")

    progress = st.progress(0)
    status_text = st.empty()
    found_counter = st.empty()

    hh_api = "https://api.hh.kz/vacancies"
    per_page = 100
    area_id = 160  # Алматы

    vacancies = []
    seen_ids = set()

    total_steps = len(title_keywords) * 50  # условная оценка
    step = 0

    for keyword in title_keywords:

        page = 0
        status_text.write(f"🔎 Ищу по ключевому слову: **{keyword}** (страница {page})")

        while True:

            params = {"text": keyword, "area": area_id, "per_page": per_page, "page": page}
            headers = {"User-Agent": "Mozilla/5.0"}

            try:
                r = requests.get(hh_api, params=params, headers=headers, timeout=10)
                if r.status_code != 200:
                    time.sleep(1)
                    continue

                data = r.json()
                items = data.get("items", [])

                if not items:
                    break

                for vac in items:

                    vac_id = vac.get("id")
                    if vac_id in seen_ids:
                        continue
                    seen_ids.add(vac_id)

                    title = vac.get("name", "").lower()

                    # фильтр по названию
                    if not any(k in title for k in title_keywords):
                        continue
                    if any(ex in title for ex in title_exclude):
                        continue

                    # подгрузка описания
                    url = vac.get("alternate_url", "")
                    desc = fetch_full_description(url)

                    # фильтр по описанию
                    if any(ex in desc for ex in desc_exclude):
                        continue

                    if desc_keywords:
                        if desc_mode == "Хотя бы одно совпадение":
                            if not any(k in desc for k in desc_keywords):
                                continue
                        else:
                            if not all(k in desc for k in desc_keywords):
                                continue

                    # адрес
                    addr = vac.get("address")
                    address = "-"
                    if addr:
                        street = addr.get("street", "")
                        building = addr.get("building", "")
                        address = f"{street} {building}".strip() or "-"

                    # ссылка 2GIS
                    if address != "-":
                        query = f"Алматы {address}".replace(" ", "+")
                        g2 = f"https://2gis.kz/almaty/search/{query}"
                    else:
                        g2 = "-"

                    vacancies.append({
                        "ID": vac_id,
                        "Название": vac.get("name", "-"),
                        "Компания": vac.get("employer", {}).get("name", "-"),
                        "Дата": vac.get("published_at", "-")[:10],
                        "Адрес": address,
                        "HH": url,
                        "2GIS": g2
                    })

                    found_counter.write(f"📌 Найдено вакансий: **{len(vacancies)}**")

                # progress bar
                step += 1
                progress.progress(min(step / total_steps, 1.0))

                page += 1
                status_text.write(f"🔎 Ищу по ключу **{keyword}**, страница {page}")

                time.sleep(0.3)

            except:
                break

    st.success(f"Поиск завершён! Найдено: {len(vacancies)} вакансий.")

    # ---------------------------
    # OUTPUT TABLE (красиво)
    # ---------------------------
    if vacancies:

        df = pd.DataFrame(vacancies)

        # кликабельные ссылки
        df["HH"] = df["HH"].apply(lambda x: f'<a href="{x}" target="_blank">🔗 HH</a>' if x != "-" else "-")
        df["2GIS"] = df["2GIS"].apply(lambda x: f'<a href="{x}" target="_blank">📍 2GIS</a>' if x != "-" else "-")

        # стилизация таблицы
        table_html = df.to_html(escape=False, index=False)

        styled_html = f"""
        <style>
        table {{
            width: 100%;
            border-collapse: collapse;
            font-family: Arial, sans-serif;
            font-size: 15px;
        }}
        thead th {{
            background: #2c2f33;
            color: white;
            padding: 10px;
            position: sticky;
            top: 0;
            z-index: 1;
        }}
        tbody tr:nth-child(odd) {{ background: #f5f5f5; }}
        tbody tr:nth-child(even) {{ background: #ffffff; }}
        td {{
            padding: 8px;
            border: 1px solid #ddd;
        }}
        tbody tr:hover {{
            background: #e1ecff;
        }}
        a {{
            text-decoration: none;
            font-weight: bold;
        }}
        </style>
        {table_html}
        """

        st.markdown(styled_html, unsafe_allow_html=True)

        # Excel (чистый)
        excel_buffer = io.BytesIO()
        pd.DataFrame(vacancies).to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        st.download_button(
            label="⬇ Скачать Excel",
            data=excel_buffer,
            file_name="vacancies.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
