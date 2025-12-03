import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime

st.set_page_config(page_title="HH Vacancies", layout="wide")
st.title("Поиск вакансий на HH")

# --- Настройки ---
keywords_input = st.text_area("Ключевые слова (через запятую)", 
                              "продукт менеджер,product manager,продакт менеджер,менеджер продуктов,менеджер по продуктам,менеджер по продукту,менеджер продукта,продуктолог,эксперт по продукту,продуктовый эксперт,продуктовый менеджер")
exclude_input = st.text_area("Исключить слова (через запятую)", "БАДы,рецепт,здравоохран")
keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
exclude_keywords = [e.strip() for e in exclude_input.split(",") if e.strip()]

area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"

vacancies = []

if st.button("Начать поиск"):
    progress_text = st.empty()
    for keyword in keywords:
        page = 0
        progress_text.text(f"Идет поиск по ключевому слову: {keyword}")
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

    if vacancies:
        df = pd.DataFrame(vacancies)
        df['published_date'] = pd.to_datetime(df['published_at']).dt.date
        df.sort_values('published_date', ascending=False, inplace=True)

        # --- Генерация HTML таблицы ---
        table_html = "<table style='border-collapse: collapse; width: 100%; color: black;'>"
        table_html += "<tr style='background-color:#f2f2f2; color: black;'><th>Вакансия</th><th>Компания</th><th>Ключевое слово</th><th>Дата публикации</th><th>Зарплата</th><th>Адрес</th></tr>"

        for _, row in df.iterrows():
            salary_text = f"{row['salary_from']} - {row['salary_to']} {row['currency']}" if row['salary_from'] != "-" else "-"
            vacancy_link = f"<a href='{row['url']}' target='_blank'>{row['title']}</a>"
            if row['address'] != "-":
                query = f"{city}, {row['address']}".replace(" ", "+")
                address_link = f"<a href='https://2gis.kz/almaty/search/{query}' target='_blank'>{row['address']}</a>"
            else:
                address_link = "-"

            table_html += f"<tr style='color:black; padding:5px;'>"
            table_html += f"<td>{vacancy_link}</td>"
            table_html += f"<td>{row['company']}</td>"
            table_html += f"<td>{row['keyword']}</td>"
            table_html += f"<td>{row['published_date']}</td>"
            table_html += f"<td>{salary_text}</td>"
            table_html += f"<td>{address_link}</td>"
            table_html += "</tr>"

        table_html += "</table>"

        st.markdown(table_html, unsafe_allow_html=True)

        # --- Скачивание CSV ---
        csv_data = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("Скачать CSV", csv_data, file_name="vacancies.csv", mime="text/csv")
    else:
        st.info("Вакансий не найдено по заданным ключевым словам.")
