import streamlit as st
import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
import io

st.set_page_config(page_title="HH Full Vacancy Scraper", layout="wide")
st.title("HH Full Vacancy Scraper (Title + Description Parsing)")

# ---------------------------
# Ввод ключевых слов и исключений
# ---------------------------
title_keywords_input = st.text_area(
    "Введите ключевые слова для поиска в названии вакансии (через запятую):",
    value="product manager,продукт менеджер"
)

title_exclude_input = st.text_area(
    "Введите слова для исключения в названии вакансии (через запятую):",
    value="стажер,intern"
)

desc_keywords_input = st.text_area(
    "Введите ключевые слова для поиска в описании вакансии (через запятую):",
    value="Firebase,Amplitude"
)

desc_exclude_input = st.text_area(
    "Введите слова для исключения в описании вакансии (через запятую):",
    value="1C,водитель"
)

desc_mode = st.radio(
    "Как применять ключевые слова для описания вакансии?",
    ["Хотя бы одно совпадение", "Все слова должны совпасть"]
)

# ---------------------------
# Преобразуем в списки
# ---------------------------
title_keywords = [t.strip().lower() for t in title_keywords_input.split(",") if t.strip()]
title_exclude = [t.strip().lower() for t in title_exclude_input.split(",") if t.strip()]
desc_keywords = [t.strip().lower() for t in desc_keywords_input.split(",") if t.strip()]
desc_exclude = [t.strip().lower() for t in desc_exclude_input.split(",") if t.strip()]

# ---------------------------
# Функция для получения полного описания вакансии
# ---------------------------
def fetch_full_description(url):
    """Загружает HTML вакансии и возвращает весь текст описания"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        html = requests.get(url, headers=headers, timeout=10)
        if html.status_code != 200:
            return ""
        soup = BeautifulSoup(html.text, "lxml")
        container = soup.find("div", {"data-qa": "vacancy-description"})
        if not container:
            return ""
        text = container.get_text(separator=" ", strip=True)
        return " ".join(text.split()).lower()
    except:
        return ""

# ---------------------------
# Запуск поиска
# ---------------------------
if st.button("Запустить поиск"):

    st.info("Начинаю поиск…")
    vacancies = []
    seen_ids = set()

    hh_api = "https://api.hh.kz/vacancies"
    per_page = 100
    area_id = 160  # Алматы

    for keyword in title_keywords:
        page = 0
        while True:
            params = {"text": keyword, "area": area_id, "per_page": per_page, "page": page}
            headers = {"User-Agent": "Mozilla/5.0"}
            try:
                r = requests.get(hh_api, params=params, headers=headers, timeout=10)
                if r.status_code != 200:
                    break
            except:
                break

            data = r.json()
            items = data.get("items", [])
            if not items:
                break

            for vac in items:
                vac_id = vac.get("id")
                title = vac.get("name", "-").lower()

                # --- фильтрация по названию ---
                if not any(k in title for k in title_keywords):
                    continue
                if any(ex in title for ex in title_exclude):
                    continue

                # --- защита от дублей по ID ---
                if vac_id in seen_ids:
                    continue
                seen_ids.add(vac_id)

                # --- Получаем полное описание ---
                url = vac.get("alternate_url", "-")
                full_desc = fetch_full_description(url)

                # --- фильтрация по описанию ---
                if desc_exclude and any(ex in full_desc for ex in desc_exclude):
                    continue
                if desc_keywords:
                    if desc_mode == "Хотя бы одно совпадение":
                        if not any(k in full_desc for k in desc_keywords):
                            continue
                    else:
                        if not all(k in full_desc for k in desc_keywords):
                            continue

                addr = vac.get("address")
                address = "-"
                if addr:
                    street = addr.get("street", "")
                    building = addr.get("building", "")
                    address = f"{street} {building}".strip() or "-"

                vacancies.append({
                    "ID": vac_id,
                    "Название": vac.get("name", "-"),
                    "Компания": vac.get("employer", {}).get("name", "-"),
                    "Дата публикации": vac.get("published_at", "-")[:10],
                    "Адрес": address,
                    "Ссылка": url
                })

            page += 1
            time.sleep(0.25)

    # ---------------------------
    # Вывод результатов
    # ---------------------------
    st.success(f"Поиск завершен! Найдено {len(vacancies)} вакансий.")

    if vacancies:
        df = pd.DataFrame(vacancies)
        st.write(df)

        # Выгрузка в Excel
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        st.download_button(
            label="Скачать Excel",
            data=excel_buffer,
            file_name="vacancies.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
