import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import io
import re
import altair as alt

st.set_page_config(page_title="HH Vacancies App", layout="wide")

st.title("HH Vacancies Scraper")

# Ввод ключевых слов для названия вакансии
keywords_input = st.text_area(
    "Введите ключевые слова для поиска в названии вакансии (через запятую):",
    value="продукт менеджер,product manager,продакт менеджер,менеджер продукта"
)

# Ввод исключающих слов
exclude_input = st.text_area(
    "Введите слова для исключения из названия вакансии (через запятую):",
    value="БАДы,рецепт,здравоохран,фарм,pharm"
)

# Ввод позитивных слов для описания
desc_include_input = st.text_area(
    "Введите ключевые слова для поиска в описании вакансии (через запятую):",
    value="аналитика,data,sql,product,маркетинг"
)

# Ввод негативных слов для описания
desc_exclude_input = st.text_area(
    "Введите слова для исключения в описании вакансии (через запятую):",
    value="продажи,официант,курьер"
)

# Режим совпадения
match_mode = st.radio(
    "Как применять ключевые слова?",
    ["Хотя бы одно совпадение", "Все слова должны совпасть"]
)

keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
exclude_keywords = [k.strip() for k in exclude_input.split(",") if k.strip()]
desc_include_keywords = [k.strip() for k in desc_include_input.split(",") if k.strip()]
desc_exclude_keywords = [k.strip() for k in desc_exclude_input.split(",") if k.strip()]

# API данные
area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"

vacancies = []


def highlight_text(text, words):
    if not text:
        return "-"
    for w in words:
        pattern = re.compile(re.escape(w), re.IGNORECASE)
        text = pattern.sub(
            fr'<span style="background-color: yellow; font-weight: bold;">\g<0></span>',
            text,
        )
    return text


if st.button("Запустить поиск"):

    progress_text = st.empty()

    for keyword in keywords:
        progress_text.text(f"Поиск по слову: {keyword}")
        page = 0

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
                descr = vac.get("snippet", {}).get("responsibility", "")

                # Исключающие слова в TITLE
                if any(ex.lower() in title.lower() for ex in exclude_keywords):
                    continue

                # Фильтрация по ключевым словам в TITLE
                title_words = title.lower()

                if match_mode == "Все слова должны совпасть":
                    if not all(k.lower() in title_words for k in keywords):
                        continue
                else:
                    if not any(k.lower() in title_words for k in keywords):
                        continue

                # Фильтрация описания
                descr_low = descr.lower()

                if any(ex.lower() in descr_low for ex in desc_exclude_keywords):
                    continue

                if desc_include_keywords:
                    if not any(w.lower() in descr_low for w in desc_include_keywords):
                        continue

                # Подсветка
                title_highlighted = highlight_text(title, keywords)
                descr_highlighted = highlight_text(descr, desc_include_keywords)

                salary = vac.get("salary")
                addr = vac.get("address")
                address = "-"
                if addr:
                    parts = [addr.get("street", ""), addr.get("building", "")]
                    address = ", ".join([p for p in parts if p]) or "-"

                vacancies.append({
                    "Название вакансии": title_highlighted,
                    "Компания": vac.get("employer", {}).get("name", "-"),
                    "Ключевое слово": keyword,
                    "Дата публикации": vac.get("published_at", "-")[:10],
                    "Описание": descr_highlighted,
                    "Адрес": address,
                    "Ссылка HH": vac.get("alternate_url", "-"),
                })

            page += 1
            time.sleep(0.2)

    st.success(f"Поиск завершён. Найдено {len(vacancies)} вакансий.")

    if vacancies:
        df = pd.DataFrame(vacancies)

        # Вывод таблицы
        st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

        # 🔥 АНАЛИТИКА: Частота упоминаний навыков
        st.header("Аналитика навыков")

        skill_freq = {}

        for skill in desc_include_keywords:
            count = sum(skill.lower() in str(desc).lower() for desc in df["Описание"])
            skill_freq[skill] = count

        df_skills = pd.DataFrame({
            "Навык": list(skill_freq.keys()),
            "Количество": list(skill_freq.values())
        })

        chart = (
            alt.Chart(df_skills)
            .mark_bar()
            .encode(
                x="Количество:Q",
                y=alt.Y("Навык:N", sort="-x"),
                tooltip=["Навык", "Количество"]
            )
            .properties(height=400)
        )

        st.altair_chart(chart, use_container_width=True)

        # Excel
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        st.download_button(
            "Скачать Excel",
            excel_buffer,
            "vacancies.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
