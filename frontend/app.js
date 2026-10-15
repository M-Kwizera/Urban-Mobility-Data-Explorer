let currentPage = 1;
let pageSize = 15;
let currentSortBy = 'pickup_datetime';
let currentSortDir = 'DESC';
let hourlyChartInstance = null;
let topZonesChartInstance = null;
let mapInstance = null;

document.addEventListener('DOMContentLoaded', async () => {
    populateHourDropdown();
    await checkHealth();
    await loadDashboardData();

    document.getElementById('filter-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        currentPage = 1;
        await loadDashboardData();
    });

    document.getElementById('reset-btn').addEventListener('click', async () => {
        document.getElementById('filter-form').reset();
        currentPage = 1;
        await loadDashboardData();
    });

    document.getElementById('prev-page').addEventListener('click', async () => {
        if (currentPage > 1) {
            currentPage--;
            await loadTripsTable();
        }
    });

    document.getElementById('next-page').addEventListener('click', async () => {
        currentPage++;
        await loadTripsTable();
    });

    document.querySelectorAll('#trips-table th[data-sort]').forEach(th => {
        th.addEventListener('click', async () => {
            const sortBy = th.getAttribute('data-sort');
            if (currentSortBy === sortBy) {
                currentSortDir = currentSortDir === 'ASC' ? 'DESC' : 'ASC';
            } else {
                currentSortBy = sortBy;
                currentSortDir = 'DESC';
            }
            currentPage = 1;
            await loadTripsTable();
        });
    });
});

function populateHourDropdown() {
    const select = document.getElementById('filter-hour');
    for (let i = 0; i < 24; i++) {
        const opt = document.createElement('option');
        opt.value = i;
        opt.textContent = `${i}:00`;
        select.appendChild(opt);
    }
}

async function checkHealth() {
    const badge = document.getElementById('health-status');
    try {
        const res = await fetchAPI('/health');
        if (res.status === 'ok') {
            badge.textContent = 'API Connected';
            badge.className = 'status-badge ok';
        } else {
            throw new Error();
        }
    } catch (err) {
        badge.textContent = 'API Connection Failed';
        badge.className = 'status-badge error';
    }
}

async function loadDashboardData() {
    await Promise.all([
        loadSummaryStats(),
        loadTripsTable(),
        loadCharts(),
        loadMap()
    ]);
}

function getFilterParams() {
    return {
        hour: document.getElementById('filter-hour').value,
        min_distance: document.getElementById('filter-min-distance').value,
        borough: document.getElementById('filter-borough').value
    };
}

async function loadSummaryStats() {
    try {
        const stats = await fetchAPI('/stats', getFilterParams());
        document.getElementById('stat-total-trips').textContent = stats.total_trips ? stats.total_trips.toLocaleString() : '0';
        document.getElementById('stat-avg-fare').textContent = stats.avg_fare ? `$${stats.avg_fare.toFixed(2)}` : '$0.00';
        document.getElementById('stat-avg-distance').textContent = stats.avg_distance ? `${stats.avg_distance.toFixed(2)} mi` : '0.00 mi';
        document.getElementById('stat-avg-speed').textContent = stats.avg_speed ? `${stats.avg_speed.toFixed(1)} MPH` : '0.0 MPH';
        document.getElementById('stat-avg-duration').textContent = stats.avg_duration ? `${stats.avg_duration.toFixed(1)} min` : '0.0 min';
    } catch (err) {
        console.error("Failed to load stats", err);
    }
}

async function loadTripsTable() {
    const params = {
        ...getFilterParams(),
        page: currentPage,
        page_size: pageSize,
        sort_by: currentSortBy,
        sort_dir: currentSortDir
    };

    const tbody = document.getElementById('trips-tbody');
    tbody.innerHTML = `<tr><td colspan="6" class="text-center">Loading trips...</td></tr>`;

    try {
        const data = await fetchAPI('/trips', params);
        const trips = data.trips || [];

        document.getElementById('page-indicator').textContent = `Page ${currentPage}`;
        document.getElementById('prev-page').disabled = currentPage <= 1;
        document.getElementById('next-page').disabled = trips.length < pageSize;

        if (trips.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center">No matching trips found.</td></tr>`;
            return;
        }

        tbody.innerHTML = '';
        trips.forEach(trip => {
            const tr = document.createElement('tr');
            
            const tdTime = document.createElement('td');
            tdTime.textContent = trip.pickup_datetime;
            tr.appendChild(tdTime);

            const tdDist = document.createElement('td');
            tdDist.textContent = trip.trip_distance ? trip.trip_distance.toFixed(2) : '-';
            tr.appendChild(tdDist);

            const tdFare = document.createElement('td');
            tdFare.textContent = trip.fare_amount ? `$${trip.fare_amount.toFixed(2)}` : '-';
            tr.appendChild(tdFare);

            const tdDur = document.createElement('td');
            tdDur.textContent = trip.duration_minutes ? `${trip.duration_minutes.toFixed(1)}` : '-';
            tr.appendChild(tdDur);

            const tdSpeed = document.createElement('td');
            tdSpeed.textContent = trip.average_speed_mph ? `${trip.average_speed_mph.toFixed(1)}` : '-';
            tr.appendChild(tdSpeed);

            const tdZone = document.createElement('td');
            tdZone.textContent = trip.pickup_zone_name ? `${trip.pickup_zone_name} (${trip.pickup_borough || ''})` : (trip.pickup_location_id || '-');
            tr.appendChild(tdZone);

            tbody.appendChild(tr);
        });
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center" style="color: var(--danger);">Error loading trip records.</td></tr>`;
    }
}

async function loadCharts() {
    try {
        const hourlyData = await fetchAPI('/trips-by-hour');
        const hours = hourlyData.map(d => `${d.pickup_hour}:00`);
        const counts = hourlyData.map(d => d.trip_count);
        const speeds = hourlyData.map(d => d.avg_speed);

        const ctxHourly = document.getElementById('hourlyDemandChart').getContext('2d');
        if (hourlyChartInstance) hourlyChartInstance.destroy();

        hourlyChartInstance = new Chart(ctxHourly, {
            type: 'bar',
            data: {
                labels: hours,
                datasets: [
                    {
                        label: 'Trip Count',
                        data: counts,
                        backgroundColor: 'rgba(37, 99, 235, 0.6)',
                        borderColor: 'rgb(37, 99, 235)',
                        borderWidth: 1,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Avg Speed (MPH)',
                        data: speeds,
                        type: 'line',
                        borderColor: 'rgb(16, 185, 129)',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 2,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { type: 'linear', position: 'left', title: { display: true, text: 'Trips' } },
                    y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Speed (MPH)' } }
                }
            }
        });

        const topZones = await fetchAPI('/top-zones?n=5');
        const zoneNames = topZones.map(z => z.zone);
        const zoneCounts = topZones.map(z => z.trip_count);

        const ctxTopZones = document.getElementById('topZonesChart').getContext('2d');
        if (topZonesChartInstance) topZonesChartInstance.destroy();

        topZonesChartInstance = new Chart(ctxTopZones, {
            type: 'bar',
            data: {
                labels: zoneNames,
                datasets: [{
                    label: 'Trips',
                    data: zoneCounts,
                    backgroundColor: 'rgba(99, 102, 241, 0.7)',
                    borderColor: 'rgb(99, 102, 241)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                scales: {
                    x: { title: { display: true, text: 'Trip Count' } }
                }
            }
        });

    } catch (err) {
        console.error("Failed to load charts", err);
    }
}

async function loadMap() {
    if (!mapInstance) {
        mapInstance = L.map('map').setView([40.7128, -74.0060], 11);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap'
        }).addTo(mapInstance);
    }
}