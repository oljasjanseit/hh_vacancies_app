import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime

st.set_page_config(page_title="Вакансии HH", layout="wide")
st.title("Сбор вакансий с HH.kz")

# --- Пользовательский ввод ключевых слов ---
keywords_input = st.text_area(
    "Введите ключевые слова через запятую",
    value="продукт менеджер,product manager,продакт менеджер,менеджер продуктов"
)
exclude_input = st.text_area(
    "Введите слова для исключения через запятую",
    value="БАДы,рецепт,здравоохран"
)

keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
exclude_keywords = [k.strip() for k in exclude_input.split(",") if k.strip()]

# --- Настройки поиска ---
area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"

# Кнопка запуска
if st.button("Запустить поиск"):
    vacancies = []
    progress_text = st.empty()
    total_keywords = len(keywords)
    for idx, keyword in enumerate(keywords, 1):
        page = 0
        progress_text.text(f"Обрабатываем ключевое слово {idx}/{total_keywords}: {keyword}")
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

                    # Ссылка на 2GIS
                    if address != "-":
                        query = f"{city}, {address}".replace(" ", "+")
                        address_link = f"https://2gis.kz/almaty/search/{query}"
                    else:
                        address_link = "-"

                    vacancies.append({
                        "Название вакансии": title,
                        "Компания": vac.get("employer", {}).get("name", "-"),
                        "Ключевое слово": keyword,
                        "Дата публикации": vac.get("published_at", "-"),
                        "Зарплата": f"{salary.get('from','-')} - {salary.get('to','-')} {salary.get('currency','-')}" if salary else "-",
                        "Адрес": address,
                        "Ссылка на HH": vac.get("alternate_url", "-"),
                        "Ссылка на 2GIS": address_link
                    })
            page += 1
            time.sleep(0.2)

    progress_text.text("Сбор вакансий завершен.")

    if vacancies:
        df = pd.DataFrame(vacancies)
        df['Дата публикации'] = pd.to_datetime(df['Дата публикации']).dt.date
        df.sort_values('Дата публикации', ascending=False, inplace=True)

        st.subheader("Результаты")
        st.dataframe(df, use_container_width=True)

        # Выгрузка в Excel
        import io
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        st.download_button(
            label="Скачать Excel",
            data=excel_buffer,
            file_name="vacancies.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Вакансий не найдено.")
