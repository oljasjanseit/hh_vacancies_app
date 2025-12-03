import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="HH Vacancies", layout="wide")
st.title("Сбор вакансий с HH.kz")

# ---------------------------
# Настройки поиска
# ---------------------------
keywords = st.text_area(
    "Ключевые слова для поиска (через запятую)",
    value="продукт менеджер,product manager,продакт менеджер,менеджер продуктов,менеджер по продуктам,менеджер по продукту,менеджер продукта,продуктолог,эксперт по продукту,продуктовый эксперт,продуктовый менеджер"
).split(",")

exclude_keywords = st.text_area(
    "Исключить вакансии с ключевыми словами (через запятую)",
    value="БАДы,рецепт,здравоохран"
).split(",")

area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"

if st.button("Собрать вакансии"):
    vacancies = []

    progress_text = st.empty()
    total_keywords = len(keywords)
    
    for idx, keyword in enumerate(keywords):
        page = 0
        progress_text.text(f"Ищу вакансии по ключевому слову ({idx+1}/{total_keywords}): {keyword}")
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
                    # Формируем адрес
                    address_parts = []
                    addr = vac.get("address")
                    if addr:
                        if addr.get("street"):
                            address_parts.append(addr.get("street"))
                        if addr.get("building"):
                            address_parts.append(addr.get("building"))
                    address = ", ".join(address_parts) if address_parts else "-"

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
        today = datetime.now().date()

        st.success(f"Найдено {len(df)} вакансий!")

        # ---------------------------
        # Вывод вакансий с подсветкой
        # ---------------------------
        for _, row in df.iterrows():
            days_diff = (today - row['published_date']).days
            if days_diff <= 7:
                color = "#d4edda"  # зеленый
            elif days_diff <= 14:
                color = "#cce5ff"  # синий
            elif days_diff <= 21:
                color = "#fff3cd"  # желтый
            else:
                color = "#e2e3e5"  # серый

            # Ссылка на HH
            title_link = f"[{row['title']}]({row['url']})"

            # Ссылка на 2GIS
            if row['address'] != "-":
                query = f"{city}, {row['address']}".replace(" ", "+")
                address_link = f"[{row['address']}](https://2gis.kz/almaty/search/{query})"
            else:
                address_link = "-"

            salary_text = f"{row['salary_from']} - {row['salary_to']} {row['currency']}" if row['salary_from'] != "-" else "-"

            st.markdown(f"""
            <div style="background-color:{color}; padding:10px; margin-bottom:5px; border-radius:5px;">
            <b>Вакансия:</b> {title_link}<br>
            <b>Компания:</b> {row['company']}<br>
            <b>Ключевое слово:</b> {row['keyword']}<br>
            <b>Дата публикации:</b> {row['published_date']}<br>
            <b>Зарплата:</b> {salary_text}<br>
            <b>Адрес:</b> {address_link}
            </div>
            """, unsafe_allow_html=True)

        # ---------------------------
        # Выгрузка в CSV
        # ---------------------------
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="Скачать CSV",
            data=csv,
            file_name="vacancies.csv",
            mime="text/csv"
        )
