import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime

st.set_page_config(page_title="HH Вакансии", layout="wide")
st.title("Сбор вакансий с hh.kz")

# --- Настройки поиска ---
keywords = st.text_area(
    "Ключевые слова (через запятую):",
    "продукт менеджер,product manager,продакт менеджер,менеджер продуктов,"
    "менеджер по продуктам,менеджер по продукту,менеджер продукта,продуктолог,"
    "эксперт по продукту,продуктовый эксперт,продуктовый менеджер"
)
keywords = [k.strip() for k in keywords.split(",")]

exclude_keywords = st.text_area(
    "Исключить ключевые слова (через запятую):",
    "БАДы,рецепт,здравоохран"
)
exclude_keywords = [k.strip() for k in exclude_keywords.split(",")]

area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"

vacancies = []

if st.button("Собрать вакансии"):
    progress_text = st.empty()
    total_keywords = len(keywords)

    for idx, keyword in enumerate(keywords, 1):
        page = 0
        progress_text.text(f"Обрабатываем '{keyword}' ({idx}/{total_keywords})...")
        while True:
            params = {"text": keyword, "area": area_id, "per_page": per_page, "page": page}
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url_api, params=params, headers=headers)
            data = response.json()
            items = data.get("items", [])
            if not items:
                break
            for vac in items:
                title = vac.get("name", "")
                if keyword.lower() in title.lower() and not any(ex.lower() in title.lower() for ex in exclude_keywords):
                    salary = vac.get("salary")
                    addr = vac.get("address")
                    address = ", ".join(filter(None, [addr.get("street","") if addr else "", addr.get("building","") if addr else ""])) or "-"
                    vacancies.append({
                        "keyword": keyword,
                        "title": title,
                        "url": vac.get("alternate_url", "-"),
                        "company": vac.get("employer", {}).get("name", "-"),
                        "description": vac.get("snippet", {}).get("responsibility", "-"),
                        "published_at": vac.get("published_at", "-"),
                        "salary_from": salary.get("from", "-") if salary else "-",
                        "salary_to": salary.get("to", "-") if salary else "-",
                        "currency": salary.get("currency", "-") if salary else "-",
                        "address": address
                    })
            page += 1
            time.sleep(0.2)

    if not vacancies:
        st.warning("Вакансий не найдено.")
    else:
        df = pd.DataFrame(vacancies)
        df['published_date'] = pd.to_datetime(df['published_at']).dt.date
        df.sort_values('published_date', ascending=False, inplace=True)

        # --- Подсветка по дате ---
        today = datetime.now().date()
        def color_row(row):
            days_diff = (today - row['published_date']).days
            if days_diff <= 7:
                return ['background-color: #d4edda']*len(row)
            elif days_diff <= 14:
                return ['background-color: #cce5ff']*len(row)
            elif days_diff <= 21:
                return ['background-color: #fff3cd']*len(row)
            else:
                return ['background-color: #e2e3e5']*len(row)

        # --- Отображение таблицы ---
        st.dataframe(
            df[['title','company','keyword','published_date','salary_from','salary_to','currency','address']],
            use_container_width=True
        )

        st.markdown("**Цветовая подсветка:** зеленый ≤7 дней, синий ≤14, желтый ≤21, серый >21")

        # --- Скачивание CSV ---
        csv_file = "vacancies.csv"
        df.to_csv(csv_file, index=False, encoding="utf-8-sig")
        st.download_button("Скачать CSV", data=open(csv_file, "rb"), file_name=csv_file)
