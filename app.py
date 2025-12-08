import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import io

st.set_page_config(page_title="HH Vacancies App", layout="wide")

st.title("HH Vacancies Scraper")

# --- Ввод ключевых слов для НАЗВАНИЯ ---
keywords_input = st.text_area(
    "Введите ключевые слова для поиска в названии вакансии (через запятую):",
    value="продукт менеджер,product manager,продакт менеджер,менеджер продуктов,менеджер по продуктам,менеджер по продукту,менеджер продукта,продуктолог,эксперт по продукту,продуктовый эксперт,продуктовый менеджер"
)

exclude_input = st.text_area(
    "Введите слова для исключения в названии вакансии (через запятую):",
    value="БАДы,рецепт,здравоохран,фарм,pharm"
)

# --- Ввод ключевых слов для ОПИСАНИЯ ---
desc_keywords_input = st.text_area(
    "Введите ключевые слова для поиска в описании вакансии (через запятую):",
    value="аналитика, продукт, CRM"
)

desc_exclude_input = st.text_area(
    "Введите слова для исключения в описании вакансии (через запятую):",
    value="продажи,холодные звонки,стажировка"
)

# Преобразование списков
keywords = [k.strip().lower() for k in keywords_input.split(",") if k.strip()]
exclude_keywords = [k.strip().lower() for k in exclude_input.split(",") if k.strip()]

desc_keywords = [k.strip().lower() for k in desc_keywords_input.split(",") if k.strip()]
desc_exclude_keywords = [k.strip().lower() for k in desc_exclude_input.split(",") if k.strip()]

# API HH
area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"

vacancies = []

# --- Кнопка запуска ---
if st.button("Запустить поиск"):

    progress_text = st.empty()
    total_count = 0

    for keyword in keywords:
        page = 0
        progress_text.text(f"Идет поиск по ключевому слову: {keyword}")

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

                title = vac.get("name", "").lower()
                descr_full = (
                    (vac.get("snippet", {}).get("responsibility") or "") + " " +
                    (vac.get("snippet", {}).get("requirement") or "")
                ).lower()

                # --- Фильтр по названию ---
                cond_title_kw = any(k in title for k in keywords)
                cond_title_ex = not any(ex in title for ex in exclude_keywords)

                # --- Фильтр по описанию ---
                cond_desc_kw = any(k in descr_full for k in desc_keywords) if desc_keywords else True
                cond_desc_ex = not any(ex in descr_full for ex in desc_exclude_keywords)

                if cond_title_kw and cond_title_ex and cond_desc_kw and cond_desc_ex:
                    salary = vac.get("salary")
                    addr = vac.get("address")

                    # Адрес форматируем
                    address_parts = []
                    if addr:
                        if addr.get("street"):
                            address_parts.append(addr.get("street"))
                        if addr.get("building"):
                            address_parts.append(addr.get("building"))
                    address = ", ".join(address_parts) if address_parts else "-"

                    # Ссылка 2GIS
                    if address != "-":
                        query = f"{city}, {address}".replace(" ", "+")
                        address_link = f"https://2gis.kz/almaty/search/{query}"
                    else:
                        address_link = "-"

                    vacancies.append({
                        "Название вакансии": vac.get("name", "-"),
                        "Компания": vac.get("employer", {}).get("name", "-"),
                        "Ключевое слово": keyword,
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
        df.sort_values("Дата публикации", ascending=False, inplace=True)

        # --- Кликие ссылки ---
        def make_clickable(url):
            return f'<a href="{url}" target="_blank">Ссылка</a>' if url != "-" else "-"

        df_display = df.copy()
        df_display["Ссылка HH"] = df_display["Ссылка HH"].apply(make_clickable)
        df_display["Ссылка 2GIS"] = df_display["Ссылка 2GIS"].apply(make_clickable)

        st.write("Результаты:")
        st.write(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

        # --- Excel ---
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        st.download_button(
            label="Скачать Excel",
            data=excel_buffer,
            file_name="vacancies.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
