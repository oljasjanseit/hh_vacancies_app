import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import io
from bs4 import BeautifulSoup

st.set_page_config(page_title="HH Vacancies App", layout="wide")
st.title("HH Vacancies Scraper")

# ======================
# Ввод ключевых слов
# ======================
title_keywords_input = st.text_area(
    "Введите ключевые слова для поиска в названии вакансии (через запятую):",
    value="продукт менеджер,product manager"
)
title_exclude_input = st.text_area(
    "Введите слова для исключения для поиска в названии вакансии (через запятую):",
    value="БАДы,рецепт,здравоохран"
)
desc_keywords_input = st.text_area(
    "Введите ключевые слова для поиска в описании вакансии (через запятую):",
    value="продукт"
)
desc_exclude_input = st.text_area(
    "Введите слова для исключения в описании вакансии (через запятую):",
    value="БАДы,рецепт"
)

title_keywords = [k.strip().lower() for k in title_keywords_input.split(",") if k.strip()]
title_exclude = [k.strip().lower() for k in title_exclude_input.split(",") if k.strip()]
desc_keywords = [k.strip().lower() for k in desc_keywords_input.split(",") if k.strip()]
desc_exclude = [k.strip().lower() for k in desc_exclude_input.split(",") if k.strip()]

desc_logic = st.radio(
    "Как применять ключевые слова для описания вакансии?",
    options=["Хотя бы одно совпадение", "Все слова должны совпасть"]
)

# ======================
# Настройки HH API
# ======================
area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"

vacancies = []

# ======================
# Кнопка для запуска поиска
# ======================
if st.button("Запустить поиск"):

    progress_text = st.empty()
    total_count = 0

    for keyword in title_keywords:
        page = 0
        progress_text.text(f"Идет поиск по ключевому слову в названии: {keyword}")
        while True:
            params = {"text": keyword, "area": area_id, "per_page": per_page, "page": page}
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url_api, params=params, headers=headers)
            if response.status_code != 200:
                st.error(f"Ошибка API: {response.status_code}")
                break
            data = response.json()
            items = data.get("items", [])
            if not items:
                break
            for vac in items:
                title = vac.get("name", "")
                title_lower = title.lower()
                # фильтр по названию вакансии
                if not any(ex in title_lower for ex in title_exclude) and any(kw in title_lower for kw in title_keywords):
                    # Берем полное описание вакансии и преобразуем в текст
                    description_html = vac.get("description", "")
                    description_text = BeautifulSoup(description_html or "", "html.parser").get_text(separator=" ")
                    description_lower = description_text.lower()

                    # Фильтр по описанию
                    if desc_keywords:
                        if desc_logic == "Хотя бы одно совпадение":
                            if not any(kw in description_lower for kw in desc_keywords):
                                continue
                        else:  # Все слова должны совпасть
                            if not all(kw in description_lower for kw in desc_keywords):
                                continue
                    if any(ex in description_lower for ex in desc_exclude):
                        continue

                    # Формируем адрес
                    addr = vac.get("address")
                    address_parts = []
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

                    salary = vac.get("salary")
                    vacancies.append({
                        "Название вакансии": title,
                        "Компания": vac.get("employer", {}).get("name", "-"),
                        "Дата публикации": vac.get("published_at", "-")[:10],
                        "Зарплата": f"{salary.get('from', '-') if salary else '-'} - {salary.get('to', '-') if salary else '-'} {salary.get('currency', '-') if salary else '-'}",
                        "Адрес": address,
                        "Ссылка HH": vac.get("alternate_url", "-"),
                        "Ссылка 2GIS": address_link
                    })
            page += 1
            total_count += len(items)
            time.sleep(0.2)

    st.success(f"Поиск завершен. Найдено {len(vacancies)} вакансий.")

    if vacancies:
        df = pd.DataFrame(vacancies)
        df.drop_duplicates(subset="Ссылка HH", inplace=True)
        df.sort_values("Дата публикации", ascending=False, inplace=True)

        # Кликабельные ссылки
        def make_clickable(url):
            return f'<a href="{url}" target="_blank">Ссылка</a>' if url != "-" else "-"

        df_display = df.copy()
        df_display["Ссылка HH"] = df_display["Ссылка HH"].apply(make_clickable)
        df_display["Ссылка 2GIS"] = df_display["Ссылка 2GIS"].apply(make_clickable)

        st.write("Результаты:")
        st.write(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

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
