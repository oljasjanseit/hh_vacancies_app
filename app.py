import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="HH Вакансии", layout="wide")
st.title("Поиск вакансий на hh.kz")

# --- Настройки ---
keywords_input = st.text_area("Ключевые слова (через запятую)", 
                               "продукт менеджер,product manager,продакт менеджер,менеджер продуктов,менеджер по продуктам,менеджер по продукту,менеджер продукта,продуктолог,эксперт по продукту,продуктовый эксперт,продуктовый менеджер")
exclude_input = st.text_area("Исключающие ключевые слова (через запятую)", 
                             "БАДы,рецепт,здравоохран")
city = st.text_input("Город для ссылок 2GIS", "Алматы")
per_page = st.number_input("Количество вакансий на страницу", min_value=10, max_value=100, value=100)

keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
exclude_keywords = [k.strip() for k in exclude_input.split(",") if k.strip()]
area_id = 160

if st.button("Собрать вакансии"):
    vacancies = []
    url_api = "https://api.hh.kz/vacancies"
    progress_bar = st.progress(0)
    total_keywords = len(keywords)
    
    for idx, keyword in enumerate(keywords):
        page = 0
        st.write(f"Поиск по ключевому слову: **{keyword}**")
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
                    address_parts = []
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
        progress_bar.progress((idx + 1) / total_keywords)

    if not vacancies:
        st.warning("Вакансий не найдено.")
    else:
        # --- Обработка данных ---
        df = pd.DataFrame(vacancies)
        df['published_date'] = pd.to_datetime(df['published_at']).dt.date
        df.sort_values('published_date', ascending=False, inplace=True)
        today = datetime.now().date()
        
        # --- HTML генерация ---
        html = """
        <style>
        table { border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr.green { background-color: #d4edda; }
        tr.blue { background-color: #cce5ff; }
        tr.yellow { background-color: #fff3cd; }
        tr.gray { background-color: #e2e3e5; }
        tr:hover { background-color: #f1f1f1; }
        a { text-decoration: none; color: #1a0dab; }
        </style>
        <table>
        <tr>
        <th>Название вакансии</th>
        <th>Компания</th>
        <th>Ключевое слово</th>
        <th>Дата публикации</th>
        <th>Зарплата</th>
        <th>Адрес</th>
        </tr>
        """
        
        for _, row in df.iterrows():
            days_diff = (today - row['published_date']).days
            if days_diff <= 7:
                color_class = "green"
            elif days_diff <= 14:
                color_class = "blue"
            elif days_diff <= 21:
                color_class = "yellow"
            else:
                color_class = "gray"

            salary_text = f"{row['salary_from']} - {row['salary_to']} {row['currency']}" if row['salary_from'] != "-" else "-"

            # Ссылка на 2GIS
            if row['address'] != "-":
                query = f"{city}, {row['address']}".replace(" ", "+")
                address_link = f"<a href='https://2gis.kz/almaty/search/{query}' target='_blank'>{row['address']}</a>"
            else:
                address_link = "-"

            html += f"<tr class='{color_class}'>"
            html += f"<td><a href='{row['url']}' target='_blank'>{row['title']}</a></td>"
            html += f"<td>{row['company']}</td>"
            html += f"<td>{row['keyword']}</td>"
            html += f"<td>{row['published_date']}</td>"
            html += f"<td>{salary_text}</td>"
            html += f"<td>{address_link}</td>"
            html += "</tr>"

        html += "</table>"

        st.markdown(html, unsafe_allow_html=True)
        
        # --- CSV ---
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="Скачать CSV", data=csv, file_name="vacancies.csv", mime="text/csv")
