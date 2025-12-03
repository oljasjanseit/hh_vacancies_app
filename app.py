import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="Вакансии HH", layout="wide")
st.title("Сбор вакансий с HH.kz")

# --- Настройки поиска через интерфейс ---
keywords_input = st.text_area(
    "Ключевые слова для поиска (через запятую)",
    value="продукт менеджер,product manager,продакт менеджер,менеджер продуктов,менеджер по продуктам,менеджер по продукту,менеджер продукта,продуктолог,эксперт по продукту,продуктовый эксперт,продуктовый менеджер"
)
exclude_input = st.text_area(
    "Исключить вакансии с ключевыми словами (через запятую)",
    value="БАДы,рецепт,здравоохран"
)

keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
exclude_keywords = [e.strip() for e in exclude_input.split(",") if e.strip()]

area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"

# Кнопка запуска поиска
if st.button("Собрать вакансии"):
    vacancies = []
    progress_text = st.empty()
    total_keywords = len(keywords)
    
    for idx, keyword in enumerate(keywords, start=1):
        page = 0
        progress_text.text(f"Поиск по ключевому слову {idx}/{total_keywords}: {keyword}")
        while True:
            params = {"text": keyword, "area": area_id, "per_page": per_page, "page": page}
            headers = {"User-Agent": "Mozilla/5.0"}
            try:
                response = requests.get(url_api, params=params, headers=headers, timeout=10)
                data = response.json()
            except Exception as e:
                st.error(f"Ошибка при запросе: {e}")
                break
            
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
                        "salary_from": salary.get("from","-") if salary else "-",
                        "salary_to": salary.get("to","-") if salary else "-",
                        "currency": salary.get("currency","-") if salary else "-",
                        "address": address
                    })
            page += 1
            time.sleep(0.2)
    
    if not vacancies:
        st.warning("Вакансий не найдено")
    else:
        df = pd.DataFrame(vacancies)
        df['published_date'] = pd.to_datetime(df['published_at'], errors='coerce').dt.date
        df.sort_values('published_date', ascending=False, inplace=True)
        today = datetime.now().date()

        # --- Генерация HTML таблицы ---
        table_html = "<table style='border-collapse: collapse; width: 100%;'>"
        table_html += "<tr style='background-color:#f2f2f2;'><th>Вакансия</th><th>Компания</th><th>Ключевое слово</th><th>Дата публикации</th><th>Зарплата</th><th>Адрес</th></tr>"
        
        for _, row in df.iterrows():
            pub_date = row['published_date']
            days_diff = (today - pub_date).days if pd.notnull(pub_date) else 999

            if days_diff <= 7:
                color = "#d4edda"
            elif days_diff <= 14:
                color = "#cce5ff"
            elif days_diff <= 21:
                color = "#fff3cd"
            else:
                color = "#e2e3e5"

            salary_text = f"{row['salary_from']} - {row['salary_to']} {row['currency']}" if row['salary_from'] != "-" else "-"
            vacancy_link = f"<a href='{row['url']}' target='_blank'>{row['title']}</a>"
            if row['address'] != "-":
                query = f"{city}, {row['address']}".replace(" ", "+")
                address_link = f"<a href='https://2gis.kz/almaty/search/{query}' target='_blank'>{row['address']}</a>"
            else:
                address_link = "-"

            table_html += f"<tr style='background-color:{color}; padding:5px;'>"
            table_html += f"<td>{vacancy_link}</td>"
            table_html += f"<td>{row['company']}</td>"
            table_html += f"<td>{row['keyword']}</td>"
            table_html += f"<td>{pub_date}</td>"
            table_html += f"<td>{salary_text}</td>"
            table_html += f"<td>{address_link}</td>"
            table_html += "</tr>"
        table_html += "</table>"

        st.markdown(table_html, unsafe_allow_html=True)

        # --- Кнопка для скачивания CSV ---
        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="Скачать CSV",
            data=csv,
            file_name="vacancies.csv",
            mime="text/csv"
        )

        st.success(f"Найдено {len(df)} вакансий")
