import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime, timedelta

st.title("Список вакансий HH.kz")

# Настройки поиска
keywords = [
    "продукт менеджер","product manager","продакт менеджер","менеджер продуктов",
    "менеджер по продуктам","менеджер по продукту","менеджер продукта",
    "продуктолог","эксперт по продукту","продуктовый эксперт","продуктовый менеджер"
]
exclude_keywords = ["БАДы","рецепт","здравоохран"]
area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"  # город для ссылок 2GIS

vacancies = []

st.info("Сбор вакансий... Это может занять некоторое время.")

# Сбор вакансий
for keyword in keywords:
    page = 0
    st.write(f"Поиск по ключевому слову: {keyword}")
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

# Создание DataFrame и сортировка по дате
df = pd.DataFrame(vacancies)
df['published_date'] = pd.to_datetime(df['published_at']).dt.date
df.sort_values('published_date', ascending=False, inplace=True)

# Добавляем CSS для цветных строк
st.markdown("""
<style>
tr.green { background-color: #d4edda; color: black; }
tr.blue { background-color: #cce5ff; color: black; }
tr.yellow { background-color: #fff3cd; color: black; }
tr.gray { background-color: #e2e3e5; color: black; }
th, td { padding: 5px; }
table { border-collapse: collapse; width: 100%; }
th { background-color: #f2f2f2; text-align: left; }
tr:hover { background-color: #f1f1f1; }
a { text-decoration: none; color: #1a0dab; }
</style>
""", unsafe_allow_html=True)

# Генерация HTML таблицы
today = datetime.now().date()
html_content = "<table><tr><th>Название вакансии</th><th>Компания</th><th>Ключевое слово</th><th>Дата публикации</th><th>Зарплата</th><th>Адрес</th></tr>"

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
    
    html_content += f"<tr class='{color_class}'>"
    html_content += f"<td><a href='{row['url']}' target='_blank'>{row['title']}</a></td>"
    html_content += f"<td>{row['company']}</td>"
    html_content += f"<td>{row['keyword']}</td>"
    html_content += f"<td>{row['published_date']}</td>"
    html_content += f"<td>{salary_text}</td>"
    html_content += f"<td>{address_link}</td>"
    html_content += "</tr>"

html_content += "</table>"

# Вывод таблицы
st.markdown(html_content, unsafe_allow_html=True)
st.success("Сбор вакансий завершен!")
