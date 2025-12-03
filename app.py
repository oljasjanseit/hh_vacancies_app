import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from io import BytesIO

st.set_page_config(page_title="HH вакансии", layout="wide")
st.title("Поиск вакансий на HH")

# Ввод ключевых слов
keywords_input = st.text_input(
    "Введите ключевые слова (через запятую):",
    "продукт менеджер,product manager,продакт менеджер,менеджер продуктов,менеджер по продуктам,менеджер по продукту,менеджер продукта,продуктолог,эксперт по продукту,продуктовый эксперт,продуктовый менеджер"
)
keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

# Ввод исключаемых слов
exclude_input = st.text_input(
    "Введите исключаемые слова (через запятую):",
    "БАДы, рецепт, здравоохран"
)
exclude_keywords = [k.strip() for k in exclude_input.split(",") if k.strip()]

# Настройки поиска
area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"

# Кнопка запуска
if st.button("Запустить поиск"):
    st.info("Начинаем поиск вакансий...")
    vacancies = []

    for keyword in keywords:
        page = 0
        st.write(f"🔍 Поиск по ключевому слову: {keyword}")
        while True:
            params = {"text": keyword, "area": area_id, "per_page": per_page, "page": page}
            headers = {"User-Agent": "Mozilla/5.0"}
            try:
                response = requests.get(url_api, params=params, headers=headers, timeout=10)
                data = response.json()
            except:
                st.error("Ошибка запроса к HH API")
                break
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

    if not vacancies:
        st.warning("Вакансий не найдено.")
    else:
        df = pd.DataFrame(vacancies)
        df['published_date'] = pd.to_datetime(df['published_at']).dt.date
        df.sort_values('published_date', ascending=False, inplace=True)

        # HTML таблица с подсветкой
        today = datetime.now().date()
        html_content = """
        <style>
        table { border-collapse: collapse; width: 100%; }
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

            if row['address'] != "-":
                query = f"{city}, {row['address']}".replace(" ", "+")
                address_link = f"<a href='https://2gis.kz/almaty/search/{query}' target='_blank'>{row['address']}</a>"
            else:
                address_link = "-"

            html_content += f"<tr class='{color_class}'>"
            html_content += f"<td><a href='{row['url']}' target='_blank'>{row['title']}</a></td>"
            html_content += f"<td>{row['company']}</td>"
            html_content += f"<td>{row['keyword']}</td>"
            html_content += f"<td>{row['published_date']}</td>"
            html_content += f"<td>{salary_text}</td>"
            html_content += f"<td>{address_link}</td>"
            html_content += "</tr>"

        html_content += "</table>"
        st.markdown(html_content, unsafe_allow_html=True)
        st.success(f"Найдено вакансий: {len(df)}")

        # Кнопка скачивания CSV
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="Скачать CSV",
            data=csv,
            file_name='hh_vacancies.csv',
            mime='text/csv'
        )
