# app.py
import streamlit as st
import requests
import pandas as pd
import time
import io
import re

# optional: try to use BeautifulSoup to strip HTML; fallback to regex if not installed
try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except Exception:
    _HAS_BS4 = False

st.set_page_config(page_title="HH Vacancies App", layout="wide")
st.title("HH Vacancies Scraper — надежный поиск (title → description)")

# ----- Inputs -----
title_keywords_input = st.text_area(
    "Введите ключевые фразы для поиска в названии вакансии (через запятую, фразы целиком):",
    value="продукт менеджер,product manager"
)
title_exclude_input = st.text_area(
    "Введите слова/фразы для исключения из названия (через запятую):",
    value="БАДы,рецепт,здравоохран"
)
desc_keywords_input = st.text_area(
    "Введите ключевые слова для поиска в полном описании вакансии (через запятую):",
    value="Amplitude"
)
desc_exclude_input = st.text_area(
    "Введите слова для исключения в описании (через запятую):",
    value=""
)

desc_logic = st.radio(
    "Как применять ключевые слова для описания вакансии?",
    ("Хотя бы одно совпадение", "Все слова должны совпасть")
)

area_id = st.number_input("Area ID (HH)", value=160)
per_page = st.number_input("per_page (API)", value=100, step=1)
max_pages = st.number_input("Max страниц на ключевую фразу (во избежание долгой работы)", value=20, step=1)

# normalize lists (preserve phrases exactly but compare case-insensitive)
title_keywords = [k.strip() for k in title_keywords_input.split(",") if k.strip()]
title_exclude = [k.strip() for k in title_exclude_input.split(",") if k.strip()]
desc_keywords = [k.strip() for k in desc_keywords_input.split(",") if k.strip()]
desc_exclude = [k.strip() for k in desc_exclude_input.split(",") if k.strip()]

# precompile regex patterns for description keywords (word-boundary, case-insensitive)
def make_word_re(kw):
    # escape and match as whole word if it looks like a word, else substring
    # e.g. "Amplitude" -> \bAmplitude\b ; "C++" -> C\+\+ (no \b)
    esc = re.escape(kw)
    if re.match(r'^\w+$', kw, flags=re.UNICODE):
        pattern = re.compile(r'\b' + esc + r'\b', flags=re.IGNORECASE)
    else:
        pattern = re.compile(esc, flags=re.IGNORECASE)
    return pattern

desc_kw_patterns = [make_word_re(k) for k in desc_keywords]
desc_ex_patterns = [make_word_re(k) for k in desc_exclude]

# helper to get full plain-text description
def extract_full_text(vac):
    # prefer vac["description"] (full HTML), fallback to snippet fields
    raw = vac.get("description")
    if raw:
        if _HAS_BS4:
            text = BeautifulSoup(raw, "html.parser").get_text(separator=" ")
        else:
            # naive strip tags if bs4 not available
            text = re.sub(r'<[^>]+>', ' ', raw)
        return re.sub(r'\s+', ' ', text).strip()
    # fallback to snippet fields
    snippet = vac.get("snippet") or {}
    req = snippet.get("requirement") or ""
    resp = snippet.get("responsibility") or ""
    text = f"{req} {resp}"
    return re.sub(r'\s+', ' ', text).strip()

# ----- Run search -----
if st.button("Запустить поиск"):
    st.info("Поиск запущен — смотрите промежуточную статистику и лог ниже.")
    url_api = "https://api.hh.kz/vacancies"
    all_candidates = []
    title_passed = []
    final_results = []
    seen_urls = set()

    # counters for diagnostics
    total_fetched = 0
    total_title_candidates = 0
    total_desc_candidates = 0

    for tk in title_keywords:
        page = 0
        while page < int(max_pages):
            params = {"text": tk, "area": int(area_id), "per_page": int(per_page), "page": page}
            headers = {"User-Agent": "Mozilla/5.0 (hh-scraper)"}
            try:
                r = requests.get(url_api, params=params, headers=headers, timeout=15)
            except Exception as e:
                st.error(f"Ошибка запроса к API: {e}")
                page = int(max_pages)  # прекратить цикл по страницам для этой фразы
                break

            if r.status_code != 200:
                st.error(f"HTTP {r.status_code} при запросе страницы {page} фразы '{tk}'")
                break

            data = r.json()
            items = data.get("items", []) or []
            total_fetched += len(items)
            if not items:
                break

            # этап 1: фильтр по названию (phrase match, case-insensitive)
            for vac in items:
                title = (vac.get("name") or "").strip()
                title_low = title.lower()
                # exclude by any title_exclude (case-insensitive substring)
                if any(te.lower() in title_low for te in title_exclude):
                    continue
                # require at least one title keyword phrase to be substring (case-insensitive)
                if not any(tk_phrase.lower() in title_low for tk_phrase in title_keywords):
                    continue
                total_title_candidates += 1
                # store candidate with description text
                full_text = extract_full_text(vac)
                all_candidates.append((vac, title, full_text))
            page += 1
            time.sleep(0.15)

    # stage counters report
    st.write(f"Всего вакансий загружено из API: {total_fetched}")
    st.write(f"Прошло фильтр по названию (candidates): {total_title_candidates}")

    # этап 2: фильтрация по описанию (используем full_text)
    for vac, title, full_text in all_candidates:
        desc = (full_text or "").strip()
        desc_lower = desc.lower()
        # check exclusions in description first
        if desc_ex_patterns and any(p.search(desc) for p in desc_ex_patterns):
            continue
        # if no desc_keywords specified => accept (we only filter by desc if provided)
        if not desc_kw_patterns:
            matched = True
        else:
            if desc_logic == "Хотя бы одно совпадение":
                matched = any(p.search(desc) for p in desc_kw_patterns)
            else:  # all words must match
                matched = all(p.search(desc) for p in desc_kw_patterns)
        if not matched:
            continue
        # deduplicate by alternate_url
        url = vac.get("alternate_url") or vac.get("alternate_url_alt") or ""
        if not url:
            # if no url, form unique key from employer+title+published_at
            url = f"{vac.get('employer',{}).get('name','')}_{title}_{vac.get('published_at','')}"
        if url in seen_urls:
            continue
        seen_urls.add(url)
        total_desc_candidates += 1

        # build result row
        salary = vac.get("salary") or {}
        salary_text = "-"
        if salary:
            salary_text = f"{salary.get('from','-')} - {salary.get('to','-')} {salary.get('currency','-')}"
        addr = vac.get("address") or {}
        address_parts = []
        if addr.get("street"):
            address_parts.append(addr.get("street"))
        if addr.get("building"):
            address_parts.append(addr.get("building"))
        address = ", ".join(address_parts) if address_parts else "-"
        address_link = f"https://2gis.kz/almaty/search/{(address or '').replace(' ','+')}" if address != "-" else "-"

        # collect matched title keywords (all that appear in title)
        matched_title_phrases = [tk for tk in title_keywords if tk.lower() in (title or "").lower()]

        final_results.append({
            "Название вакансии": title,
            "Компания": vac.get("employer", {}).get("name", "-"),
            "Ключи в названии": "; ".join(matched_title_phrases),
            "Дата публикации": (vac.get("published_at") or "")[:10],
            "Зарплата": salary_text,
            "Адрес": address,
            "Ссылка HH": vac.get("alternate_url", "-"),
            "Ссылка 2GIS": address_link,
            "Описание (фрагмент)": (desc[:500] + "...") if desc else "-"
        })

    # final diagnostics
    st.write(f"Прошло фильтр по описанию: {total_desc_candidates}")

    if not final_results:
        st.warning("После всех фильтров вакансий не найдено. Проверь, пожалуйста, сочетание title_keywords / title_exclude и desc_keywords.")
    else:
        df = pd.DataFrame(final_results)
        df.sort_values("Дата публикации", ascending=False, inplace=True)

        # кликабельные ссылки
        def linkify(u):
            return f'<a href="{u}" target="_blank">Открыть</a>' if u and u != "-" else "-"
        df_display = df.copy()
        df_display["Ссылка HH"] = df_display["Ссылка HH"].apply(linkify)
        df_display["Ссылка 2GIS"] = df_display["Ссылка 2GIS"].apply(linkify)

        st.write("Результаты:")
        st.write(df_display.to_html(escape=False, index=False), unsafe_allow_html=True)

        # Excel export
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, engine="openpyxl")
        excel_buffer.seek(0)
        st.download_button("Скачать Excel (.xlsx)", excel_buffer.getvalue(), file_name="vacancies.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
