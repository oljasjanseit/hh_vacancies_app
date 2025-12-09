import streamlit as st
import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
import io

st.set_page_config(page_title="HH FULL Vacancy Scraper", layout="wide")
st.title("HH FULL Vacancy Scraper (Title + Description Parsing)")

# ---------------------------
# ВВОД ПАРАМЕТРОВ
# ---------------------------
title_keywords_input = st.text_area(
    "Введите ключевые слова для поиска в названии вакансии (через запятую):",
    value="продукт менеджер, product manager"
)

title_exclude_input = st.text_area(
    "Введите слова для исключения в названии вакансии (через запятую):",
    value="стажер,intern"
)

desc_keywords_input = st.text_area(
    "Введите ключевые слова для поиска в описании вакансии (через запятую):",
    value="Firebase,Amplitude"
)

desc_exclude_input = st.text_area(
    "Введите слова для исключения в описании вакансии (через запятую):",
    value="1C,водитель"
)

desc_mode = st.radio(
    "Как применять ключевые слова для описания вакансии?",
    ["Хотя бы одно совпадение", "Все слова должны совпасть"]
)

# ---------------------------
# ПРЕОБРАЗОВАНИЕ СПИСКОВ
# ---------------------------
title_keywords = [t.strip().lower() for t in title_keywords_input.split(",") if t.strip()]
title_exclude = [t.strip().lower() for t in title_exclude_input.split(",") if t.strip()]
desc_keywords = [t.strip().lower() for t in desc_keywords_input.split(",") if t.strip()]
desc_exclude = [t.strip().lower() for t in desc_exclude_input.split(",") if t.strip()]

# ---------------------------
# Функция получения полного описания
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
# ЗАПУСК ПОИСКА
# ---------------------------
if st.button("Запустить поиск"):

    st.info("Начинаю поиск…")
    vacancies = []
    seen_ids = set()

    hh_api = "https://api.hh.ru/vacancies"
    per_page = 100
    area_id = 160  # Алматы

    progress_bar = st.progress(0)
    status_text = st.empty()

    total_keywords = len(title_keywords)
    keyword_index = 0

    for keyword in title_keywords:
        keyword_index += 1
        page = 0
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
                    title = vac.get("name", "").lower()
                    # --- фильтрация по названию ---
                    if not any(k in title for k in title_keywords):
                        continue
                    if any(ex in title for ex in title_exclude):
                        continue
                    # --- защита от дублей ---
                    if vac_id in seen_ids:
                        continue
                    seen_ids.add(vac_id)
                    # --- Грузим полный HTML ---
                    url = vac.get("alternate_url", "")
                    full_desc = fetch_full_description(url)
                    # --- фильтрация по описанию ---
                    if desc_exclude and any(ex in full_desc for ex in desc_exclude):
                        continue
                    if desc_keywords:
                        if desc_mode == "Хотя бы одно совпадение":
                            if not any(k in full_desc for k in desc_keywords):
                                continue
                        else:
                            if not all(k in full_desc for k in desc_keywords):
                                continue
                    addr = vac.get("address")
                    address = "-"
                    if addr:
                        street = addr.get("street", "")
                        building = addr.get("building", "")
                        address = f"{street} {building}".strip() or "-"
                    # --- Ссылка на 2GIS ---
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
                # Обновляем прогресс
                progress_value = min((keyword_index - 1 + page/50)/total_keywords, 1.0)
                progress_bar.progress(progress_value)
                status_text.text(f"Обрабатываем ключевое слово {keyword_index}/{total_keywords}, страница {page}, вакансий найдено: {len(vacancies)}")
                time.sleep(0.2)
            except:
                break

    st.success(f"Поиск завершен! Найдено {len(vacancies)} вакансий.")

    if vacancies:
        df = pd.DataFrame(vacancies)

        # Кликабельные ссылки
        df_display = df.copy()
        df_display["Ссылка HH"] = df_display["Ссылка HH"].apply(lambda x: f'<a href="{x}" target="_blank">🔗 Открыть HH</a>' if x != "-" else "-")
        df_display["Ссылка 2GIS"] = df_display["Ссылка 2GIS"].apply(lambda x: f'<a href="{x}" target="_blank">📍 2GIS</a>' if x != "-" else "-")

        # Отображение через markdown таблицу с HTML
        table_html = "<table style='width:100%; border-collapse: collapse;'>"
        # Заголовки
        table_html += "<tr>"
        for col in df_display.columns:
            table_html += f"<th style='border: 1px solid #ccc; padding: 6px;'>{col}</th>"
        table_html += "</tr>"
        # Данные
        for _, row in df_display.iterrows():
            table_html += "<tr>"
            for col in df_display.columns:
                table_html += f"<td style='border: 1px solid #ccc; padding: 6px;'>{row[col]}</td>"
            table_html += "</tr>"
        table_html += "</table>"

        st.markdown(table_html, unsafe_allow_html=True)

        # Выгрузка Excel
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        st.download_button(
            label="Скачать Excel",
            data=excel_buffer,
            file_name="vacancies.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
