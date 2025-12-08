import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import io

st.set_page_config(page_title="HH Vacancies App", layout="wide")
st.title("HH Vacancies Scraper")

# ======= Ввод ключевых слов =======
# Название вакансии
keywords_title_input = st.text_area(
    "Введите ключевые слова для поиска в названии вакансии (через запятую):",
    value="продукт менеджер,product manager,продакт менеджер,менеджер продуктов,менеджер по продуктам,менеджер по продукту,менеджер продукта,продуктолог,эксперт по продукту,продуктовый эксперт,продуктовый менеджер"
)
exclude_title_input = st.text_area(
    "Введите слова для исключения в названии вакансии (через запятую):",
    value="БАДы,рецепт,здравоохран,фарм,pharm"
)
# Описание вакансии
keywords_desc_input = st.text_area(
    "Введите ключевые слова для поиска в описании вакансии (через запятую):",
    value="продукт"
)
exclude_desc_input = st.text_area(
    "Введите слова для исключения в описании вакансии (через запятую):",
    value="БАДы,рецепт,здравоохран,фарм,pharm"
)

# Как применять ключевые слова для описания вакансии
match_option = st.radio(
    "Как применять ключевые слова для описания вакансии?",
    ["Хотя бы одно совпадение", "Все слова должны совпасть"]
)

# Преобразуем ввод в списки
keywords_title = [k.strip() for k in keywords_title_input.split(",") if k.strip()]
exclude_title = [k.strip() for k in exclude_title_input.split(",") if k.strip()]
keywords_desc = [k.strip() for k in keywords_desc_input.split(",") if k.strip()]
exclude_desc = [k.strip() for k in exclude_desc_input.split(",") if k.strip()]

# ======= Настройки HH API =======
area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"

vacancies = []

if st.button("Запустить поиск"):
    progress_text = st.empty()
    total_count = 0
    seen_links = set()  # для удаления дублей

    for keyword in keywords_title:
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
                if not any(ex.lower() in title.lower() for ex in exclude_title) and keyword.lower() in title.lower():
                    # ======= Описание вакансии =======
                    snippet = vac.get("snippet") or {}
                    description = snippet.get("requirement", "") + " " + snippet.get("responsibility", "")

                    # Проверка ключевых слов в описании
                    desc_match = True
                    if keywords_desc:
                        if match_option == "Хотя бы одно совпадение":
                            desc_match = any(k.lower() in description.lower() for k in keywords_desc)
                        else:  # Все слова должны совпасть
                            desc_match = all(k.lower() in description.lower() for k in keywords_desc)

                    # Исключения для описания
                    if exclude_desc:
                        if any(ex.lower() in description.lower() for ex in exclude_desc):
                            desc_match = False

                    link = vac.get("alternate_url", "-")
                    if desc_match and link not in seen_links:
                        seen_links.add(link)

                        salary = vac.get("salary")
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

                        vacancies.append({
                            "Название вакансии": title,
                            "Компания": vac.get("employer", {}).get("name", "-"),
                            "Дата публикации": vac.get("published_at", "-")[:10],
                            "Зарплата": f"{salary.get('from', '-') if salary else '-'} - {salary.get('to', '-') if salary else '-'} {salary.get('currency', '-') if salary else '-'}",
                            "Адрес": address,
                            "Ссылка HH": link,
                            "Ссылка 2GIS": address_link,
                            "Описание": description
                        })
            page += 1
            total_count += len(items)
            time.sleep(0.2)

    st.success(f"Поиск завершен. Найдено {len(vacancies)} вакансий.")

    if vacancies:
        df = pd.DataFrame(vacancies)
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
