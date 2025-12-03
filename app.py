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
                    addr = vac.get("address")
                    address_parts = []
                    if addr:
                        if addr.get("street"):
                            address_parts.append(addr.get("street"))
                        if addr.get("building"):
                            address_parts.append(addr.get("building"))
                    address = ", ".join(address_parts) if address_parts else "-"

                    # 2GIS ссылка
                    if address != "-":
                        query = f"{city}, {address}".replace(" ", "+")
                        address_link = f"https://2gis.kz/almaty/search/{query}"
                    else:
                        address_link = "-"

                    vacancies.append({
                        "Вакансия": f"[{title}]({vac.get('alternate_url','-')})",
                        "Компания": vac.get("employer", {}).get("name", "-"),
                        "Ключевое слово": keyword,
                        "Дата публикации": vac.get("published_at", "-"),
                        "Зарплата": f"{salary.get('from','-')} - {salary.get('to','-')} {salary.get('currency','-')}" if salary else "-",
                        "Адрес": f"[{address}]({address_link})" if address_link != "-" else "-"
                    })
            page += 1
            time.sleep(0.2)

    if not vacancies:
        st.warning("Вакансий не найдено.")
    else:
        df = pd.DataFrame(vacancies)
        # Оставляем только дату для сортировки
        df['Дата публикации сортировка'] = pd.to_datetime(df['Дата публикации'], errors='coerce').dt.date
        df.sort_values('Дата публикации сортировка', ascending=False, inplace=True)
        df.drop(columns='Дата публикации сортировка', inplace=True)

        st.success(f"Найдено {len(df)} вакансий!")

        # HTML таблица с подсветкой по дате
        today = datetime.now().date()
        table_html = "<table style='border-collapse: collapse; width: 100%;'>"
        table_html += "<tr style='background-color:#f2f2f2;'><th>Вакансия</th><th>Компания</th><th>Ключевое слово</th><th>Дата публикации</th><th>Зарплата</th><th>Адрес</th></tr>"

        for _, row in df.iterrows():
            try:
                pub_date = pd.to_datetime(row['Дата публикации'], errors='coerce').date()
                days_diff = (today - pub_date).days if pub_date else 999
            except:
                pub_date = None
                days_diff = 999

            if days_diff <= 7:
                color = "#d4edda"
            elif days_diff <= 14:
                color = "#cce5ff"
            elif days_diff <= 21:
                color = "#fff3cd"
            else:
                color = "#e2e3e5"

            table_html += f"<tr style='background-color:{color}; padding:5px;'>"
            for col in df.columns:
                table_html += f"<td>{row[col]}</td>"
            table_html += "</tr>"

        table_html += "</table>"

        st.markdown(table_html, unsafe_allow_html=True)

        # Кнопка для скачивания CSV
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button("Скачать CSV", data=csv, file_name="vacancies.csv", mime="text/csv")
