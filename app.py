import streamlit as st
import requests
import pandas as pd
import time
import io

st.set_page_config(page_title="HH Vacancies App", layout="wide")
st.title("HH Vacancies Scraper")

# --- Ввод ключевых слов ---
title_keywords_input = st.text_area(
    "Введите ключевые слова для поиска в названии вакансии (через запятую):",
    value="продукт менеджер,product manager"
)
title_exclude_input = st.text_area(
    "Введите слова для исключения из названия вакансии (через запятую):",
    value="БАДы,рецепт,здравоохран,фарм,pharm"
)
desc_keywords_input = st.text_area(
    "Введите ключевые слова для поиска в описании вакансии (через запятую):",
    value="продукт"
)
desc_exclude_input = st.text_area(
    "Введите слова для исключения из описания вакансии (через запятую):",
    value=""
)

desc_logic = st.radio(
    "Как применять ключевые слова для описания вакансии?",
    ("Хотя бы одно совпадение", "Все слова должны совпасть")
)

title_keywords = [k.strip().lower() for k in title_keywords_input.split(",") if k.strip()]
title_exclude = [k.strip().lower() for k in title_exclude_input.split(",") if k.strip()]
desc_keywords = [k.strip().lower() for k in desc_keywords_input.split(",") if k.strip()]
desc_exclude = [k.strip().lower() for k in desc_exclude_input.split(",") if k.strip()]

# --- Настройки API ---
area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"
vacancies = []

# --- Кнопка запуска ---
if st.button("Запустить поиск"):
    progress_text = st.empty()
    
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
                
                # --- Фильтр по названию ---
                if not any(tk in title_lower for tk in title_keywords):
                    continue
                if any(te in title_lower for te in title_exclude):
                    continue
                
                # --- Формируем описание ---
                snippet = vac.get("snippet") or {}
                description = (snippet.get("requirement", "") or "") + " " + (snippet.get("responsibility", "") or "")
                description_lower = description.lower()
                
                # --- Фильтр по описанию ---
                desc_pass = True
                if desc_keywords:
                    if desc_logic == "Хотя бы одно совпадение":
                        desc_pass = any(dk in description_lower for dk in desc_keywords)
                    else:  # Все слова должны совпасть
                        desc_pass = all(dk in description_lower for dk in desc_keywords)
                if desc_exclude:
                    if any(de in description_lower for de in desc_exclude):
                        desc_pass = False
                        
                if not desc_pass:
                    continue
                
                # --- Адрес ---
                addr = vac.get("address") or {}
                address_parts = [addr.get("street", ""), addr.get("building", "")]
                address = ", ".join([a for a in address_parts if a]) or "-"
                address_link = f"https://2gis.kz/almaty/search/{city.replace(' ', '+')},{address.replace(' ', '+')}" if address != "-" else "-"
                
                # --- Зарплата ---
                salary = vac.get("salary") or {}
                salary_text = f"{salary.get('from','-')} - {salary.get('to','-')} {salary.get('currency','-')}" if salary else "-"
                
                # --- Сохраняем вакансию ---
                vacancies.append({
                    "Название вакансии": title,
                    "Компания": vac.get("employer", {}).get("name", "-"),
                    "Ключевое слово": keyword,
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
        # --- Убираем дубли по ссылке HH ---
        df = pd.DataFrame(vacancies).drop_duplicates(subset=["Ссылка HH"])
        df.sort_values("Дата публикации", ascending=False, inplace=True)
        
        # --- Кликабельные ссылки ---
        df_display = df.copy()
        df_display["Ссылка HH"] = df_display["Ссылка HH"].apply(lambda x: f'<a href="{x}" target="_blank">Ссылка</a>' if x != "-" else "-")
        df_display["Ссылка 2GIS"] = df_display["Ссылка 2GIS"].apply(lambda x: f'<a href="{x}" target="_blank">Ссылка</a>' if x != "-" else "-")
        
        st.write(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)
        
        # --- Выгрузка Excel ---
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, engine="openpyxl")
        excel_buffer.seek(0)
        st.download_button(
            label="Скачать Excel",
            data=excel_buffer,
            file_name="vacancies.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
