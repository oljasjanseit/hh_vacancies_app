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
    value="продукт менеджер,product manager"
)
title_exclude_input = st.text_area(
    "Введите слова для исключения для поиска в названии вакансии (через запятую):",
    value=""
)
desc_keywords_input = st.text_area(
    "Введите ключевые слова для поиска в описании вакансии (через запятую):",
    value="продукт"
)
desc_exclude_input = st.text_area(
    "Введите слова для исключения в описании вакансии (через запятую):",
    value=""
)

desc_mode = st.radio(
    "Как применять ключевые слова для описания вакансии?",
    ("Хотя бы одно совпадение", "Все слова должны совпасть")
)

# Преобразуем в списки и в нижний регистр
title_keywords = [k.strip().lower() for k in title_keywords_input.split(",") if k.strip()]
title_exclude = [k.strip().lower() for k in title_exclude_input.split(",") if k.strip()]
desc_keywords = [k.strip().lower() for k in desc_keywords_input.split(",") if k.strip()]
desc_exclude = [k.strip().lower() for k in desc_exclude_input.split(",") if k.strip()]

# Настройки HH API
area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"

vacancies = []

# Кнопка запуска поиска
if st.button("Запустить поиск"):
    progress_text = st.empty()
    
    for title_keyword in title_keywords:
        page = 0
        while True:
            progress_text.text(f"Идет поиск по ключевому слову в названии: {title_keyword}")
            params = {"text": title_keyword, "area": area_id, "per_page": per_page, "page": page}
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
                title = vac.get("name", "").lower()
                # Фильтруем по названию
                if not any(ex in title for ex in title_exclude) and any(k in title for k in title_keywords):
                    description = ""
                    snippet = vac.get("snippet") or {}
                    description = (snippet.get("requirement") or "") + " " + (snippet.get("responsibility") or "")
                    description_lower = description.lower()

                    # Фильтрация по описанию
                    if desc_keywords:
                        if desc_mode == "Хотя бы одно совпадение":
                            if not any(k in description_lower for k in desc_keywords):
                                continue
                        else:
                            if not all(k in description_lower for k in desc_keywords):
                                continue
                    if desc_exclude:
                        if any(ex in description_lower for ex in desc_exclude):
                            continue

                    # Зарплата
                    salary = vac.get("salary")
                    salary_text = f"{salary.get('from', '-') if salary else '-'} - {salary.get('to', '-') if salary else '-'} {salary.get('currency', '-') if salary else '-'}"

                    # Адрес
                    addr = vac.get("address") or {}
                    address_parts = []
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
                        "Название вакансии": vac.get("name", "-"),
                        "Компания": vac.get("employer", {}).get("name", "-"),
                        "Ключевое слово в названии": title_keyword,
                        "Дата публикации": vac.get("published_at", "-")[:10],
                        "Зарплата": salary_text,
                        "Адрес": address,
                        "Ссылка HH": vac.get("alternate_url", "-"),
                        "Ссылка 2GIS": address_link
                    })
            page += 1
            time.sleep(0.2)

    st.success(f"Поиск завершен. Найдено {len(vacancies)} вакансий.")

    if vacancies:
        # Убираем дубли по ссылке
        df = pd.DataFrame(vacancies).drop_duplicates(subset=["Ссылка HH"])
        df.sort_values("Дата публикации", ascending=False, inplace=True)

        # Кликабельные ссылки
        def make_clickable(url):
            return f'<a href="{url}" target="_blank">Ссылка</a>' if url != "-" else "-"

        df_display = df.copy()
        df_display["Ссылка HH"] = df_display["Ссылка HH"].apply(make_clickable)
        df_display["Ссылка 2GIS"] = df_display["Ссылка 2GIS"].apply(make_clickable)

        st.write("Результаты:")
        st.write(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

        # Excel выгрузка
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        st.download_button(
            label="Скачать Excel",
            data=excel_buffer,
            file_name="vacancies.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
