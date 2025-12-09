<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8" />
<title>HH Search Tool</title>
<style>
    body {
        font-family: Arial, sans-serif;
        background: #f5f7fa;
        margin: 20px;
    }

    h2 {
        margin-bottom: 15px;
    }

    .container {
        max-width: 1100px;
        margin: auto;
        background: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.08);
    }

    label {
        display: block;
        margin-top: 10px;
        font-weight: bold;
    }

    input {
        padding: 8px;
        width: 100%;
        margin-top: 5px;
        border-radius: 6px;
        border: 1px solid #ccc;
    }

    button {
        padding: 10px 20px;
        margin-top: 15px;
        background: #4CAF50;
        color: white;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        font-size: 15px;
    }

    button:hover {
        background: #45a049;
    }

    .progress {
        width: 100%;
        background: #eee;
        height: 22px;
        border-radius: 10px;
        overflow: hidden;
        margin-top: 20px;
    }

    .progress-bar {
        height: 100%;
        width: 0%;
        background: #4CAF50;
        transition: width 0.25s;
    }

    .status-text {
        margin-top: 10px;
        font-size: 15px;
        font-weight: bold;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 25px;
        background: #fff;
        border-radius: 10px;
        overflow: hidden;
    }

    th, td {
        border-bottom: 1px solid #ddd;
        padding: 8px 10px;
        text-align: left;
    }

    th {
        background: #f0f0f0;
        font-weight: bold;
    }

    tr:hover {
        background: #f9f9f9;
    }

    .small-btn {
        padding: 5px 8px;
        border-radius: 6px;
        font-size: 13px;
        text-decoration: none;
        background: #3498db;
        color: white;
    }

    .small-btn:hover {
        background: #2980b9;
    }
</style>
</head>

<body>

<div class="container">
    <h2>Поиск вакансий HH.kz с фильтром по ключевому слову</h2>

    <label>Город / Регион (area)</label>
    <input id="area" value="160" />

    <label>Ключевое слово (ищется в описании вакансии)</label>
    <input id="keyword" value="firebase" />

    <button onclick="startSearch()">Начать поиск</button>

    <div class="progress">
        <div id="progressBar" class="progress-bar"></div>
    </div>

    <div id="status" class="status-text"></div>

    <table id="resultsTable">
        <thead>
            <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Компания</th>
                <th>Дата</th>
                <th>Адрес</th>
                <th>HH</th>
                <th>2GIS</th>
            </tr>
        </thead>
        <tbody></tbody>
    </table>
</div>

<script>
async function startSearch() {
    const area = document.getElementById("area").value.trim();
    const keyword = document.getElementById("keyword").value.trim().toLowerCase();

    const progressBar = document.getElementById("progressBar");
    const status = document.getElementById("status");
    const tableBody = document.querySelector("#resultsTable tbody");
    tableBody.innerHTML = "";

    status.textContent = "Запрашиваю данные…";

    let page = 0;
    const perPage = 100;
    let totalPages = 1;

    const foundVacancies = [];

    while (page < totalPages) {
        const url = `https://api.hh.ru/vacancies?area=${area}&page=${page}&per_page=${perPage}`;

        status.textContent = `Обрабатываю страницу ${page + 1}…`;

        const response = await fetch(url);
        const data = await response.json();

        totalPages = Math.min(20, data.pages); // HH ограничивает максимум 20 страниц
        const items = data.items || [];

        // Просмотр вакансий страницы
        for (const v of items) {
            const full = await fetch(v.url).then(r => r.json());
            const text = (full.description || "").toLowerCase();

            if (text.includes(keyword)) {
                foundVacancies.push({
                    id: v.id,
                    name: v.name,
                    company: v.employer ? v.employer.name : "-",
                    date: v.published_at.split("T")[0],
                    address: v.address ? v.address.raw : "-",
                    hh: v.alternate_url
                });
            }
        }

        // Обновление прогресса
        progressBar.style.width = (((page + 1) / totalPages) * 100) + "%";

        status.textContent =
            `Страниц обработано: ${page + 1} из ${totalPages} | Найдено подходящих вакансий: ${foundVacancies.length}`;

        page++;
    }

    // Вывод результатов
    foundVacancies.forEach(v => {
        const row = document.createElement("tr");

        row.innerHTML = `
            <td>${v.id}</td>
            <td>${v.name}</td>
            <td>${v.company}</td>
            <td>${v.date}</td>
            <td>${v.address}</td>
            <td><a class="small-btn" href="${v.hh}" target="_blank">Открыть</a></td>
            <td>${
                v.address !== "-" 
                ? `<a class="small-btn" target="_blank"
                     href="https://2gis.kz/almaty/search/${encodeURIComponent(v.address)}">2GIS</a>`
                : "-"
            }</td>
        `;

        tableBody.appendChild(row);
    });

    status.textContent = `Готово! Найдено всего: ${foundVacancies.length}`;
    progressBar.style.width = "100%";
}
</script>

</body>
</html>
