import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import io

st.set_page_config(page_title="HH Вакансии", layout="wide")

st.title("Поиск вакансий по ключевым словам на HH.kz")

# --- Настройки поиска ---
keywords = st.text_area(
    "Введите ключевые слова через запятую",
    value="продукт менеджер,product manager,продакт менеджер,менеджер продуктов,менеджер по продуктам,менеджер по продукту,менеджер продукта,продуктолог,эксперт по продукту,продуктовый эксперт,продуктовый менеджер"
).split(",")
keywords = [k.strip() for k in keywords if k.strip()]

exclude_keywords = st.text_area(
    "Исключить вакансии по ключевым словам (через запятую)",
    value="БАДы,рецепт,здравоохран"
).split(",")
exclude_keywords = [k.strip() for k in exclude_keywords if k.strip()]

area_id = 160  # Алматы
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"

if st.button("Начать поиск"):
    vacancies = []
    progress_text = st.empty()
    
    for keyword in keywords:
        page = 0
        progress_text.text(f"Ищем вакансии по ключевому слову: {keyword}")
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
                    address_parts = []
                    addr = vac.get("address")
                    if addr:
                        if addr.get("street"):
                            address_parts.append(addr.get("street"))
                        if addr.get("building"):
                            address_parts.append(addr.get("building"))
                    address = ", ".join(address_parts) if address_parts else "-"
                    
                    # Ссылка на 2GIS
                    if address != "-":
                        query = f"{city}, {address}".replace(" ", "+")
                        address_link = f"https://2gis.kz/almaty/search/{query}"
                    else:
                        address_link = "-"
                    
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
                        "address": address,
                        "address_link": address_link
                    })
            page += 1
            time.sleep(0.2)
    
    if not vacancies:
        st.warning("Вакансий не найдено")
    else:
        df = pd.DataFrame(vacancies)
        df['published_date'] = pd.to_datetime(df['published_at']).dt.date
        df.sort_values('published_date', ascending=False, inplace=True)
        
        # --- Таблица в Streamlit ---
        def make_clickable(url, text):
            return f'<a href="{url}" target="_blank">{text}</a>'

        df_display = df.copy()
        df_display['title'] = df.apply(lambda x: make_clickable(x['url'], x['title']), axis=1)
        df_display['address'] = df.apply(lambda x: make_clickable(x['address_link'], x['address']) if x['address_link']!="-"
                                         else "-", axis=1)
        df_display['salary'] = df.apply(lambda x: f"{x['salary_from']} - {x['salary_to']} {x['currency']}" if x['salary_from'] != "-" else "-", axis=1)
        
        df_display = df_display[['title','company','keyword','published_date','salary','address']]
        
        st.markdown(
            df_display.to_html(escape=False, index=False),
            unsafe_allow_html=True
        )
        
        # --- CSV скачивание ---
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
        st.download_button(
            label="Скачать CSV",
            data=csv_buffer.getvalue(),
            file_name="vacancies.csv",
            mime="text/csv"
        )
