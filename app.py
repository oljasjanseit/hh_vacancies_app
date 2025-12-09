import streamlit as st
import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
import io

st.set_page_config(page_title="HH FULL Vacancy Scraper", layout="wide")
st.title("HH FULL Vacancy Scraper (Title + Description Parsing)")

# ---------------------------
# INPUTS
# ---------------------------
title_keywords_input = st.text_area(
    "Ключевые слова в названии вакансии (через запятую):",
    value="продукт менеджер, product manager, продакт менеджер, менеджер продуктов, менеджер по продуктам, менеджер по продукту, менеджер продукта, продуктолог, эксперт по продукту, продуктовый эксперт, продуктовый менеджер"
)

title_exclude_input = st.text_area(
    "Исключить слова в названии (через запятую):",
    value="стажер,intern"
)

desc_keywords_input = st.text_area(
    "Ключевые слова в описании вакансии (через запятую):",
    value="Firebase,Amplitude"
)

desc_exclude_input = st.text_area(
    "Исключить слова в описании (через запятую):",
    value="1C,водитель"
)

desc_mode = st.radio(
    "Как применять ключевые слова в описании?",
    ["Хотя бы одно совпадение", "Все слова должны совпасть"]
)

# Преобразование списков
title_keywords = [t.strip().lower() for t in title_keywords_input.split(",") if t.strip()]
title_exclude = [t.strip().lower() for t in title_exclude_input.split(",") if t.strip()]
desc_keywords = [t.strip().lower() for t in desc_keywords_input.split(",") if t.strip()]
desc_exclude = [t.strip().lower() for t in desc_exclude_input.split(",") if t.strip()]

# ---------------------------
# FULL DESCRIPTION PARSER
# ---------------------------
def fetch_full_description(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        html = requests.get(url, headers=headers, timeout=8)
        if html.status_code != 200:
            return ""
        soup = BeautifulSoup(html.text, "lxml")
        container = soup.find("div", {"data-qa": "vacancy-description"})
        if not container:
            return ""
        text = container.get_text(separator=" ", strip=True)
        text = " ".join(text.replace("\n", " ").split())
        return text.lower()
    except:
        return ""

# ---------------------------
# START SEARCH
# ---------------------------
if st.button("Запустить поиск"):

    st.info("Начинаю поиск…")

    vacancies = []
    seen_ids = set()

    hh_api = "https://api.hh.kz/vacancies"
    per_page = 100
    area_id = 160  # Алматы

    progress = st.progress(0)
    current_cycle = 0

    for keyword in title_keywords:
        page = 0

        while True:
            params = {"text": keyword, "area": area_id, "per_page": per_page, "page": page}
            headers = {"User-Agent": "Mozilla/5.0"}

            try:
                r = requests.get(hh_api, params=params, headers=headers, timeout=15)
                if r.status_code != 200:
                    time.sleep(1)
                    continue

                data = r.json()
                items = data.get("items", [])

                if not items:
                    break

                for vac in items:
                    vac_id = vac.get("id")
                    title = vac.get("name", "").lower()

                    # Фильтрация названия
                    if not any(k in title for k in title_keywords):
                        continue
                    if any(ex in title for ex in title_exclude):
                        continue

                    # Дубликаты
                    if vac_id in seen_ids:
                        continue
                    seen_ids.add(vac_id)

                    # HTML описания
                    url = vac.get("alternate_url", "")
                    full_desc = fetch_full_description(url)

                    # Фильтрация описания
                    if desc_exclude and any(ex in full_desc for ex in desc_exclude):
                        continue

                    if desc_keywords:
                        if desc_mode == "Хотя бы одно совпадение":
                            if not any(k in full_desc for k in desc_keywords):
                                continue
                        else:
                            if not all(k in full_desc for k in desc_keywords):
                                continue

                    # Адрес
                    addr = vac.get("address")
                    address = "-"
                    if addr:
                        street = addr.get("street", "")
                        building = addr.get("building", "")
                        address = f"{street} {building}".strip() or "-"

                    # 2GIS URL
                    if address != "-":
                        query = f"Алматы, {address}".replace(" ", "+")
                        address_link = f"https://2gis.kz/almaty/search/{query}"
                    else:
                        address_link = "-"

                    vacancies.append({
                        "ID": vac_id,
                        "Название": vac.get("name", "-"),
                        "Компания": vac.get("employer", {}).get("name", "-"),
                        "Дата публикации": vac.get("published_at", "-")[:10],
                        "Адрес": address,
                        "Ссылка HH": url,
                        "Ссылка 2GIS": address_link
                    })

                page += 1
                current_cycle += 1
                progress.progress(min(current_cycle / 50, 1.0))

                time.sleep(0.2)

            except:
                break

    progress.progress(1.0)

    st.success(f"Поиск завершен! Найдено {len(vacancies)} вакансий.")

    # ---------------------------
    # OUTPUT TABLE
    # ---------------------------
    if vacancies:
        df = pd.DataFrame(vacancies)

        # Превращаем ссылки в HTML
        df_display = df.copy()
        df_display["Ссылка HH"] = df_display["Ссылка HH"].apply(
            lambda x: f'<a href="{x}" target="_blank">🔗 Открыть HH</a>' if x != "-" else "-"
        )
        df_display["Ссылка 2GIS"] = df_display["Ссылка 2GIS"].apply(
            lambda x: f'<a href="{x}" target="_blank">📍 2GIS</a>' if x != "-" else "-"
        )

        html_table = df_display.to_html(
            escape=False,
            index=False,
            border=0,
            classes="styled-table"
        )

        # CSS + таблица
        full_html = f"""
        <style>
            .styled-table {{
                border-collapse: collapse;
                width: 100%;
                font-family: Arial, sans-serif;
            }}
            .styled-table thead th {{
                background: #1f2937;
                color: #fff;
                padding: 8px;
                border-bottom: 2px solid #444;
                position: sticky;
                top: 0;
                z-index: 2;
            }}
            .styled-table tbody tr:nth-child(odd) {{
                background: #f9f9f9;
            }}
            .styled-table tbody tr:hover {{
                background: #eef6ff;
            }}
            .styled-table td {{
                padding: 8px;
                border-bottom: 1px solid #ddd;
                vertical-align: top;
            }}
            a {{
                color: #0d6efd;
                font-weight: bold;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
        </style>
        {html_table}
        """

        st.html(full_html)

        # Excel export
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        st.download_button(
            label="⬇ Скачать Excel",
            data=excel_buffer,
            file_name="vacancies.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
