import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import io

st.set_page_config(page_title="HH Vacancies App", layout="wide")
st.title("HH Vacancies Scraper")

# Ввод ключевых слов
title_keywords_input = st.text_area(
    "Введите ключевые слова для поиска в названии вакансии (через запятую):",
    value="продукт менеджер,product manager,продакт менеджер,менеджер продуктов,менеджер по продуктам,менеджер по продукту,менеджер продукта,продуктолог,эксперт по продукту,продуктовый эксперт,продуктовый менеджер"
)
title_exclude_input = st.text_area(
    "Введите слова для исключения для поиска в названии вакансии (через запятую):",
    value="БАДы,рецепт,здравоохран,фарм,pharm"
)
desc_keywords_input = st.text_area(
    "Введите ключевые слова для поиска в описании вакансии (через запятую):",
    value="продукт"
)
desc_exclude_input = st.text_area(
    "Введите слова для исключения в описании вакансии (через запятую):",
    value=""
)

title_keywords = [k.strip() for k in title_keywords_input.split(",") if k.strip()]
title_exclude = [k.strip() for k in title_exclude_input.split(",") if k.strip()]
desc_keywords = [k.strip() for k in desc_keywords_input.split(",") if k.strip()]
desc_exclude = [k.strip() for k in desc_exclude_input.split(",") if k.strip()]

# Опция поиска по описанию
match_option = st.radio(
    "Как применять ключевые слова для описания вакансии?",
    ["Хотя бы одно совпадение", "Все слова должны совпасть"]
)

# Настройки HH API
area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"

vacancies = []

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
                if not title or any(ex.lower() in title.lower() for ex in title_exclude):
                    continue
                if not any(k.lower() in title.lower() for k in [keyword]):
                    continue  # фильтр по названию

                snippet = vac.get("snippet") or {}
                description = (snippet.get("requirement") or "") + " " + (snippet.get("responsibility") or "")
                description_lower = description.lower()

                # Фильтр по ключевым словам описания
                if desc_keywords:
                    if match_option == "Хотя бы одно совпадение":
                        desc_match = any(k.lower() in description_lower for k in desc_keywords)
                    else:
                        desc_match = all(k.lower() in description_lower for k in desc_keywords)
                else:
                    desc_match = True

                # Исключение по словам в описании
                if desc_exclude:
                    if any(ex.lower() in description_lower for ex in desc_exclude):
                        desc_match = False

                if not desc_match:
                    continue

                salary = vac.get("salary")
                addr = vac.get("address") or {}
                address_parts = []
                if addr.get("street"):
                    address_parts.append(addr.get("street"))
                if addr.get("building"):
                    address_parts.append(addr.get("building"))
                address = ", ".join(address_parts) if address_parts else "-"

                # 2GIS ссылка
                address_link = f"https://2gis.kz/almaty/search/{city.replace(' ','+')},{address.replace(' ','+')}" if address != "-" else "-"

                vacancy_entry = {
                    "Название вакансии": title,
                    "Компания": vac.get("employer", {}).get("name", "-"),
                    "Ключевое слово": keyword,
                    "Дата публикации": vac.get("published_at", "-")[:10],
                    "Зарплата": f"{salary.get('from', '-') if salary else '-'} - {salary.get('to', '-') if salary else '-'} {salary.get('currency', '-') if salary else '-'}",
                    "Адрес": address,
                    "Ссылка HH": vac.get("alternate_url", "-"),
                    "Ссылка 2GIS": address_link
                }

                # Проверка дубликата по ссылке
                if vacancy_entry["Ссылка HH"] not in [v["Ссылка HH"] for v in vacancies]:
                    vacancies.append(vacancy_entry)

            page += 1
            total_count += len(items)
            time.sleep(0.2)

    st.success(f"Поиск завершен. Найдено {len(vacancies)} вакансий.")

    if vacancies:
        df = pd.DataFrame(vacancies)
        df.sort_values("Дата публикации", ascending=False, inplace=True)

        # Отображение с кликабельными ссылками
        def make_clickable(url):
            return f'<a href="{url}" target="_blank">Ссылка</a>' if url != "-" else "-"

        df_display = df.copy()
        df_display["Ссылка HH"] = df_display["Ссылка HH"].apply(make_clickable)
        df_display["Ссылка 2GIS"] = df_display["Ссылка 2GIS"].apply(make_clickable)

        st.write("Результаты:")
        st.write(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

        # Выгрузка в Excel
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        st.download_button(
            label="Скачать Excel",
            data=excel_buffer,
            file_name="vacancies.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
