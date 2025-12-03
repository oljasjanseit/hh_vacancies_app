import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime
import io

st.set_page_config(page_title="Вакансии HH", layout="wide")
st.title("Поиск вакансий на HH.kz")

# --- Настройки поиска ---
keywords = st.text_area(
    "Введите ключевые слова через запятую",
    value="продукт менеджер,product manager,продакт менеджер,менеджер продуктов,менеджер по продуктам,менеджер по продукту,менеджер продукта,продуктолог,эксперт по продукту,продуктовый эксперт,продуктовый менеджер"
).split(",")
keywords = [k.strip() for k in keywords if k.strip()]

exclude_keywords = st.text_area(
    "Исключить вакансии по ключевым словам (через запятую)",
    value="БАДы,рецепт,здравоохран"
).split(",")
exclude_keywords = [k.strip() for k in exclude_keywords if k.strip()]

area_id = 160
per_page = 100
url_api = "https://api.hh.kz/vacancies"
city = "Алматы"

if st.button("Начать поиск"):
    vacancies = []
    progress_text = st.empty()

    for keyword in keywords:
        page = 0
        progress_text.text(f"Ищем вакансии по ключевому слову: {keyword}")
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
                    if addr:
                        address = ", ".join(filter(None, [addr.get("street",""), addr.get("building","")]))
                    else:
                        address = "-"
                    if address != "-":
                        query = f"{city}, {address}".replace(" ", "+")
                        address_link = f"https://2gis.kz/almaty/search/{query}"
                    else:
                        address_link = "-"
                    vacancies.append({
                        "Ключевое слово": keyword,
                        "Название вакансии": title,
                        "Компания": vac.get("employer", {}).get("name","-"),
                        "Дата публикации": vac.get("published_at","-"),
                        "Зарплата": f"{salary.get('from','-')} - {salary.get('to','-')} {salary.get('currency','-')}" if salary else "-",
                        "Адрес": address,
                        "Ссылка на HH": vac.get("alternate_url","-"),
                        "Ссылка на 2GIS": address_link
                    })
            page += 1
            time.sleep(0.2)
    
    if not vacancies:
        st.warning("Вакансий не найдено")
    else:
        df = pd.DataFrame(vacancies)
        df['Дата публикации'] = pd.to_datetime(df['Дата публикации']).dt.date
        df.sort_values('Дата публикации', ascending=False, inplace=True)
        
        # --- Таблица в Streamlit ---
        def make_clickable(url, text):
            return f'<a href="{url}" target="_blank">{text}</a>'
        
        df_display = df.copy()
        df_display['Название вакансии'] = df.apply(lambda x: make_clickable(x['Ссылка на HH'], x['Название вакансии']), axis=1)
        df_display['Адрес'] = df.apply(lambda x: make_clickable(x['Ссылка на 2GIS'], x['Адрес']) if x['Ссылка на 2GIS']!="-"
                                       else "-", axis=1)
        
        df_display_show = df_display[['Название вакансии','Компания','Ключевое слово','Дата публикации','Зарплата','Адрес']]
        
        st.markdown(
            df_display_show.to_html(escape=False, index=False),
            unsafe_allow_html=True
        )
        
        # --- CSV выгрузка с UTF-8 BOM для Excel ---
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
        st.download_button(
            label="Скачать CSV",
            data=csv_buffer.getvalue(),
            file_name="vacancies.csv",
            mime="text/csv"
        )
