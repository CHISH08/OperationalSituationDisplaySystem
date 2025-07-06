// Глобальные переменные
let map;
let mapLayer; 
let satelliteLayer;
let searchRectangle = null;
let startLatLng = null;
let markers = [];

/**
 * Функция разбора даты/времени по отдельным полям
 */
function parseDateTimeFromFields(day, month, year, hour, minute, second, isStart) {
  if (!year.trim()) {
    return null;
  }
  let y = parseInt(year, 10);
  if (isNaN(y) || y < 1 || y > 9999) {
    return { error: "Некорректный год" };
  }
  let m, d, hh, min, ss;
  if (!month.trim()) {
    m = isStart ? 1 : 12;
  } else {
    m = parseInt(month, 10);
    if (isNaN(m) || m < 1 || m > 12) {
      return { error: "Некорректный месяц" };
    }
  }
  const lastDayOfMonth = new Date(y, m, 0).getDate();
  if (!day.trim()) {
    d = isStart ? 1 : lastDayOfMonth;
  } else {
    d = parseInt(day, 10);
    if (isNaN(d) || d < 1 || d > lastDayOfMonth) {
      return { error: "Некорректный день" };
    }
  }
  if (!hour.trim()) {
    hh = isStart ? 0 : 23;
  } else {
    hh = parseInt(hour, 10);
    if (isNaN(hh) || hh < 0 || hh > 23) {
      return { error: "Некорректный час" };
    }
  }
  if (!minute.trim()) {
    min = isStart ? 0 : 59;
  } else {
    min = parseInt(minute, 10);
    if (isNaN(min) || min < 0 || min > 59) {
      return { error: "Некорректная минута" };
    }
  }
  if (!second.trim()) {
    ss = isStart ? 0 : 59;
  } else {
    ss = parseInt(second, 10);
    if (isNaN(ss) || ss < 0 || ss > 59) {
      return { error: "Некорректная секунда" };
    }
  }

  const mmStr = String(m).padStart(2, "0");
  const ddStr = String(d).padStart(2, "0");
  const hhStr = String(hh).padStart(2, "0");
  const minStr = String(min).padStart(2, "0");
  const ssStr = String(ss).padStart(2, "0");
  return `${y}-${mmStr}-${ddStr}T${hhStr}:${minStr}:${ssStr}`;
}

function initMap() {
  map = L.map('map', {
      attributionControl: false,
      center: [0, 0],
      zoom: 2,
      maxZoom: 20,
      minZoom: 2,
      zoomControl: false,
      dragging: true,
      touchZoom: true,
      scrollWheelZoom: true,
      doubleClickZoom: true,
      boxZoom: true,
      keyboard: true,
      tap: true
  });

  // Перемещаем зум-контрол в левый нижний угол
  L.control.zoom({ position: 'bottomleft' }).addTo(map);

  mapLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 20,
      attribution: '© OpenStreetMap contributors'
  }).addTo(map);

  satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 20,
      attribution: 'Tiles &copy; Esri'
  });

  L.control.scale({
      position: 'bottomleft',
      imperial: false,
      maxWidth: 200
  }).addTo(map);

  // Возможность выделения прямоугольной области (Ctrl + клик)
  map.on('click', function (e) {
      if (e.originalEvent.ctrlKey) {
          if (!startLatLng) {
              startLatLng = e.latlng;
              const tempRectangle = L.rectangle([startLatLng, startLatLng], { color: 'blue' }).addTo(map);
              map.on('mousemove', function (moveEvent) {
                  if (startLatLng) {
                      tempRectangle.setBounds([startLatLng, moveEvent.latlng]);
                  }
              });
          } else {
              const endLatLng = e.latlng;
              document.getElementById('search-lat-min').value = Math.min(startLatLng.lat, endLatLng.lat).toFixed(6);
              document.getElementById('search-lat-max').value = Math.max(startLatLng.lat, endLatLng.lat).toFixed(6);
              document.getElementById('search-lng-min').value = Math.min(startLatLng.lng, endLatLng.lng).toFixed(6);
              document.getElementById('search-lng-max').value = Math.max(startLatLng.lng, endLatLng.lng).toFixed(6);
              map.eachLayer(layer => {
                  if (layer instanceof L.Rectangle) {
                      map.removeLayer(layer);
                  }
              });
              startLatLng = null;
              map.off('mousemove');
          }
      }
  });
}

function showLoading() {
  document.getElementById("loading").style.display = "block";
}

function hideLoading() {
  document.getElementById("loading").style.display = "none";
}

async function performSearch() {
  const dateFields = [
    'start-day','start-month','start-year','start-hour','start-minute','start-second',
    'end-day','end-month','end-year','end-hour','end-minute','end-second'
  ];
  dateFields.forEach(f => document.getElementById(f).classList.remove('error'));

  const searchText = document.getElementById('search-text').value.trim();
  const latMin = parseFloat(document.getElementById('search-lat-min').value);
  const latMax = parseFloat(document.getElementById('search-lat-max').value);
  const lngMin = parseFloat(document.getElementById('search-lng-min').value);
  const lngMax = parseFloat(document.getElementById('search-lng-max').value);
  const topK = parseInt(document.getElementById('top-k').value);

  const sd = document.getElementById('start-day').value;
  const sm = document.getElementById('start-month').value;
  const sy = document.getElementById('start-year').value;
  const sh = document.getElementById('start-hour').value;
  const smin = document.getElementById('start-minute').value;
  const ss = document.getElementById('start-second').value;

  const ed = document.getElementById('end-day').value;
  const em = document.getElementById('end-month').value;
  const ey = document.getElementById('end-year').value;
  const eh = document.getElementById('end-hour').value;
  const emin = document.getElementById('end-minute').value;
  const es = document.getElementById('end-second').value;

  let startParsed = parseDateTimeFromFields(sd, sm, sy, sh, smin, ss, true);
  let endParsed = parseDateTimeFromFields(ed, em, ey, eh, emin, es, false);

  function markErrorStart(msg) {
    ['start-day','start-month','start-year','start-hour','start-minute','start-second']
      .forEach(f => document.getElementById(f).classList.add('error'));
    alert("Начало периода: " + msg);
  }
  function markErrorEnd(msg) {
    ['end-day','end-month','end-year','end-hour','end-minute','end-second']
      .forEach(f => document.getElementById(f).classList.add('error'));
    alert("Конец периода: " + msg);
  }

  let error = false;
  if (startParsed && typeof startParsed === 'object' && startParsed.error) {
    markErrorStart(startParsed.error);
    error = true;
  }
  if (endParsed && typeof endParsed === 'object' && endParsed.error) {
    markErrorEnd(endParsed.error);
    error = true;
  }
  if (error) return;

  if (!sy.trim()) {
    startParsed = null;
  }
  if (!ey.trim()) {
    endParsed = null;
  }

  if (
    !searchText &&
    (isNaN(latMin) || isNaN(latMax) || isNaN(lngMin) || isNaN(lngMax)) &&
    !startParsed &&
    !endParsed
  ) {
    alert('Заполните хотя бы один критерий поиска (текст, координаты или даты).');
    return;
  }

  showLoading();

  try {
    const apiUrl = 'http://localhost:8000/search';
    const requestData = {
      text: searchText,
      min_lat: isNaN(latMin) ? null : latMin,
      max_lat: isNaN(latMax) ? null : latMax,
      min_lon: isNaN(lngMin) ? null : lngMin,
      max_lon: isNaN(lngMax) ? null : lngMax,
      top_k: isNaN(topK) ? 5 : topK,
      start_datetime: startParsed || null,
      end_datetime: endParsed || null
    };

    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestData)
    });

    console.log("Статус ответа сервера:", response.status);
    if (!response.ok) {
      throw new Error(`Ошибка сервера: ${response.status} ${response.statusText}`);
    }
    const data = await response.json();
    console.log("Полученные данные от API:", data);

    clearMarkers();
    markers = [];
    document.getElementById("results-container").innerHTML = "";

    if (Array.isArray(data) && data.length > 0) {
      displayResults(data);
      document.getElementById("results-panel").classList.add("visible");
    } else {
      alert('Ничего не найдено.');
    }
  } catch (error) {
    console.error("Ошибка при выполнении запроса:", error);
    alert('Произошла ошибка при поиске.');
  } finally {
    hideLoading();
  }
}

function displayResults(results) {
  console.log("Отображение результатов:", results);
  const resultsContainer = document.getElementById("results-container");

  results.forEach((result, index) => {
    if (typeof result.lat !== 'number' || typeof result.lon !== 'number') {
      console.warn("Некорректные данные результата:", result);
      return;
    }

    let imageUrl;
    if (result.image.startsWith("http")) {
      // Извлекаем часть ключа из полного URL
      const s3Prefix = "https://storage.yandexcloud.net/";
      let key = result.image.substring(s3Prefix.length); // например, "remote-sensing-storage/geo_images/47186/photo.jpg"

      // Если ключ начинается с имени бакета, удаляем его
      const bucketName = "remote-sensing-storage";
      if (key.startsWith(bucketName + "/")) {
        key = key.substring(bucketName.length + 1);
      }

      // Формируем URL для запроса через Flask‑эндпоинт
      imageUrl = `http://127.0.0.1:8333/get_image?bucket=${bucketName}&key=${encodeURIComponent(key)}`;
    } else {
      let rel = result.image.replace(/^\/+/, '');
      // 2) Если в начале пути есть "app/datasets/", отрезаем эту часть
      rel = rel.replace(/^app\/datasets\//, '');
      // 3) Кодируем только спецсимволы, слэши не трогаем
      const safePath = encodeURI(rel);
      imageUrl = `http://127.0.0.1:8333/local_image/${safePath}`;
    }

    console.log(`Используем изображение: ${imageUrl}`);

    // Создаём маркер на карте
    const marker = L.marker([result.lat, result.lon]).addTo(map);
    const popupContent = `
      <div>
        <img src="${imageUrl}" alt="result" onclick="openModal('${imageUrl}')" /><br>
        <div style="border:1px solid #444; padding:4px; background:#333; border-radius:4px;">
          <div style="margin-bottom:4px;"><strong>⭐ Score:</strong> ${result.score}</div>
          ${
            result.date
              ? `<div style="margin-bottom:4px;"><strong>📅 Date:</strong> ${result.date.join('-')}</div>`
              : ""
          }
          ${
            result.time
              ? `<div style="margin-bottom:4px;"><strong>⏰ Time:</strong> ${result.time.join(':')}</div>`
              : ""
          }
          <div><strong>📍 Coords:</strong> Lat: ${result.lat.toFixed(6)} / Lng: ${result.lon.toFixed(6)}</div>
        </div>
      </div>
    `;
    marker.bindPopup(popupContent);

    marker.on('popupopen', () => {
      map.setView([result.lat, result.lon], 18, { animate: true });
    });

    markers.push({ marker, lat: result.lat, lon: result.lon });

    // Создаём карточку результата
    const itemDiv = document.createElement("div");
    itemDiv.classList.add("result-item");
    itemDiv.onclick = () => jumpToMarker(index);

    const imgEl = document.createElement("img");
    imgEl.src = imageUrl;

    const infoDiv = document.createElement("div");
    infoDiv.classList.add("result-info");

    const scoreCell = document.createElement("div");
    scoreCell.classList.add("info-cell");
    scoreCell.innerText = `⭐ Score: ${result.score}`;
    infoDiv.appendChild(scoreCell);

    if (result.date) {
      const dateCell = document.createElement("div");
      dateCell.classList.add("info-cell");
      dateCell.innerText = `📅 Date: ${result.date.join('-')}`;
      infoDiv.appendChild(dateCell);
    }

    if (result.time) {
      const timeCell = document.createElement("div");
      timeCell.classList.add("info-cell");
      timeCell.innerText = `⏰ Time: ${result.time.join(':')}`;
      infoDiv.appendChild(timeCell);
    }

    const coordsCell = document.createElement("div");
    coordsCell.classList.add("info-cell");
    coordsCell.innerText = `📍 Lat: ${result.lat.toFixed(6)} / Lng: ${result.lon.toFixed(6)}`;
    infoDiv.appendChild(coordsCell);

    itemDiv.appendChild(imgEl);
    itemDiv.appendChild(infoDiv);
    resultsContainer.appendChild(itemDiv);
  });
}


function jumpToMarker(index) {
  const mk = markers[index];
  if (!mk) return;
  map.setView([mk.lat, mk.lon], 18, { animate: true });
  mk.marker.openPopup();
}

function clearMarkers() {
  map.eachLayer(layer => {
    if (layer instanceof L.Marker) {
      map.removeLayer(layer);
    }
  });
}

function switchToSatelliteView() {
  if (map.hasLayer(mapLayer)) { map.removeLayer(mapLayer); }
  if (!map.hasLayer(satelliteLayer)) { map.addLayer(satelliteLayer); }
}

function switchToMapView() {
  if (map.hasLayer(satelliteLayer)) { map.removeLayer(satelliteLayer); }
  if (!map.hasLayer(mapLayer)) { map.addLayer(mapLayer); }
}

function openModal(imageSrc) {
  const modal = document.getElementById("modal");
  const modalImg = document.getElementById("modal-image");
  modal.style.display = "block";
  modalImg.src = imageSrc;
}

function closeModal() {
  const modal = document.getElementById("modal");
  modal.style.display = "none";
}

function toggleResultsPanel() {
  const panel = document.getElementById("results-panel");
  if (panel.classList.contains("hidden") || panel.style.display === "none") {
    panel.classList.remove("hidden");
    panel.classList.add("visible");
    panel.style.display = "block";
  } else {
    panel.classList.remove("visible");
    panel.classList.add("hidden");
    panel.style.display = "none";
  }
}

window.onclick = function(event) {
  const modal = document.getElementById("modal");
  if (event.target === modal) {
    modal.style.display = "none";
  }
};

document.addEventListener("keydown", function(event) {
  if (event.key === "Escape") {
    closeModal();
  }
});

document.addEventListener("DOMContentLoaded", function () {
  initMap();
});
