import streamlit as st
import requests
import pandas as pd
import time
from bs4 import BeautifulSoup

st.set_page_config(page_title="HH Vacancy Scraper", layout="wide")

st.title("HH Vacancy Scraper (Поправлено: нормальная таблица + прогресс + статус)")

# ---------------------------
# ВВОД ПАРАМЕТРОВ
# ---------------------------
area_id = 160  # Алматы

keyword = st.text_input("Ключевое слово для поиска в описании вакансии", "firebase")

start_button = st.button("Начать поиск")

# ---------------------------
# Функция получения HTML описания
# ---------------------------
def fetch_description(vac_url):
    try:
        html = requests.get(vac_url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(html.text, "lxml")
        block = soup.find("div", {"data-qa": "vacancy-description"})
        if not block:
            return ""
        return block.get_text(separator=" ", strip=True).lower()
    except:
        return ""


# =====================================================================
# ОСНОВНАЯ ЛОГИКА ПОИСКА
# =====================================================================
if start_button:

    st.info("Запуск поиска…")
    progress = st.progress(0)
    status = st.empty()

    results = []
    seen_ids = set()

    hh_api = "https://api.hh.ru/vacancies"
    per_page = 100

    # Сначала узнаем количество страниц
    first = requests.get(hh_api, params={"area": area_id, "per_page": per_page, "page": 0}).json()
    total_pages = min(first.get("pages", 1), 20)   # HH API максимум 20 страниц

    for page in range(total_pages):

        status.write(f"Обрабатываю страницу {page+1} из {total_pages}… Найдено: {len(results)} вакансий")
        progress.progress((page + 1) / total_pages)

        data = requests.get(
            hh_api,
            params={"area": area_id, "per_page": per_page, "page": page},
            headers={"User-Agent": "Mozilla/5.0"}
        ).json()

        items = data.get("items", [])

        for vac in items:

            vac_id = vac["id"]

            if vac_id in seen_ids:
                continue
            seen_ids.add(vac_id)

            url = vac.get("alternate_url")
            full_desc = fetch_description(url)

            if keyword.lower() not in full_desc:
                continue

            addr = vac.get("address")
            if addr and addr.get("raw"):
                address = addr["raw"]
                gis_link = f"https://2gis.kz/almaty/search/{address.replace(' ', '+')}"
            else:
                address = "-"
                gis_link = "-"

            results.append({
                "ID": vac_id,
                "Название": vac.get("name"),
                "Компания": vac.get("employer", {}).get("name", "-"),
                "Дата": vac.get("published_at", "").split("T")[0],
                "Адрес": address,
                "Ссылка HH": url,
                "2GIS": gis_link
            })

        time.sleep(0.25)

    st.success(f"Готово! Найдено: {len(results)} вакансий")

    if results:
        df = pd.DataFrame(results)

        # Показываем таблицу нормально (НЕ HTML!)
        st.dataframe(df, use_container_width=True)

        # Экспорт
        st.download_button(
            "Скачать Excel",
            df.to_excel(index=False, engine="openpyxl"),
            file_name="vacancies.xlsx"
        )
