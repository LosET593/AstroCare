
const socket = io();

const chartInstances = {};

const fields = [
    {
        key: "heart_rate",
        element: "heart-rate",
        status: "heart-status",
        label: "Frecuencia cardíaca",
        unit: "bpm",
        decimals: 0
    },
    {
        key: "spo2",
        element: "spo2",
        status: "spo2-status",
        label: "Saturación de oxígeno",
        unit: "%",
        decimals: 0
    },
    {
        key: "body_temperature",
        element: "temperature",
        status: "temperature-status",
        label: "Temperatura",
        unit: "°C",
        decimals: 1
    },
    {
        key: "sleep_hours",
        element: "sleep",
        status: "sleep-status",
        label: "Sueño",
        unit: "hrs",
        decimals: 1
    },
    {
        key: "glucose",
        element: "glucose",
        status: "glucose-status",
        label: "Glucosa",
        unit: "mg/dL",
        decimals: 0
    },
    {
        key: "mood_score",
        element: "mood",
        status: "mood-status",
        label: "Estado de ánimo",
        unit: "/10",
        decimals: 0
    }
];

// --------------------------------------------------
// UTILIDADES
// --------------------------------------------------

function setText(id, value) {
    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}

function normalizeStatus(status) {
    const validStatuses = [
        "normal",
        "warning",
        "critical",
        "unknown"
    ];

    const normalized = String(status || "").toLowerCase();

    return validStatuses.includes(normalized)
        ? normalized
        : "unknown";
}

function applyStatus(element, status) {
    if (!element) return;

    const state = normalizeStatus(status);

    element.textContent = state.toUpperCase();
    element.className = "metric-status " + state;
}

// --------------------------------------------------
// OBTENER ANÁLISIS DEL BACKEND
// --------------------------------------------------

function getAnalysis(data) {
    if (!data) return null;

    // Formato nuevo: analysis como objeto.
    if (
        data.analysis &&
        typeof data.analysis === "object"
    ) {
        return data.analysis;
    }

    // Compatibilidad: analysis como texto JSON.
    if (typeof data.analysis === "string") {
        try {
            return JSON.parse(data.analysis);
        } catch (error) {
            console.error("Invalid analysis JSON:", error);
        }
    }

    // Compatibilidad con registros guardados anteriormente.
    if (data.analysis_json) {
        try {
            return JSON.parse(data.analysis_json);
        } catch (error) {
            console.error("Invalid analysis_json:", error);
        }
    }

    return null;
}

// --------------------------------------------------
// INDICADORES
// --------------------------------------------------

function setIndicator(field, value, analysis) {
    const valueElement = document.getElementById(field.element);
    const statusElement = document.getElementById(field.status);

    if (valueElement) {
        const numericValue = Number(value);

        valueElement.textContent =
            value == null || !Number.isFinite(numericValue)
                ? "--"
                : numericValue.toFixed(field.decimals);
    }

    const indicatorAnalysis =
        analysis?.indicators?.[field.key];

    const state = indicatorAnalysis
        ? indicatorAnalysis.status
        : "unknown";

    applyStatus(statusElement, state);
}

function updatePressure(data, analysis) {
    const systolic = data.systolic_pressure;
    const diastolic = data.diastolic_pressure;

    if (systolic == null || diastolic == null) {
        setText("pressure", "--/--");
        applyStatus(
            document.getElementById("pressure-status"),
            "unknown"
        );
        return;
    }

    const sys = Number(systolic);
    const dia = Number(diastolic);

    if (!Number.isFinite(sys) || !Number.isFinite(dia)) {
        setText("pressure", "--/--");
        applyStatus(
            document.getElementById("pressure-status"),
            "unknown"
        );
        return;
    }

    setText(
        "pressure",
        `${sys.toFixed(0)}/${dia.toFixed(0)}`
    );

    const pressureAnalysis =
        analysis?.indicators?.blood_pressure;

    applyStatus(
        document.getElementById("pressure-status"),
        pressureAnalysis?.status
    );
}

// --------------------------------------------------
// ESTADO GENERAL
// --------------------------------------------------

function updateOverall(analysis) {
    const state = normalizeStatus(
        analysis?.overall_status
    );

    setText("overall-status", state.toUpperCase());

    const dot = document.getElementById("overall-dot");

    if (dot) {
        dot.style.background =
            state === "critical" ? "var(--red)" :
            state === "warning" ? "var(--yellow)" :
            state === "normal" ? "var(--green)" :
            "var(--muted)";
    }
}

// --------------------------------------------------
// SISTEMA DE ALERTAS
// --------------------------------------------------

function updateAlerts(analysis) {
    const container = document.getElementById("alert-list");

    if (!container) return;

    container.replaceChildren();

    if (!analysis || !analysis.indicators) {
        const message = document.createElement("p");
        message.className = "alert-item";
        message.textContent =
            "Análisis biométrico no disponible.";

        container.appendChild(message);
        return;
    }

    const labels = {
        heart_rate: "Frecuencia cardíaca",
        spo2: "Saturación de oxígeno",
        body_temperature: "Temperatura",
        glucose: "Glucosa",
        sleep_hours: "Sueño",
        mood_score: "Estado de ánimo",
        blood_pressure: "Presión arterial"
    };

    const units = {
        heart_rate: "bpm",
        spo2: "%",
        body_temperature: "°C",
        glucose: "mg/dL",
        sleep_hours: "hrs",
        mood_score: "/10"
    };

    const alerts = [];

    Object.entries(analysis.indicators).forEach(
        ([key, indicator]) => {

            const state = normalizeStatus(indicator.status);

            if (state !== "warning" && state !== "critical") {
                return;
            }

            let measurement = "";

            if (key === "blood_pressure") {
                const pressure = indicator.value;

                if (pressure) {
                    measurement =
                        `${pressure.systolic}/${pressure.diastolic} mmHg`;
                }
            } else if (indicator.value != null) {
                measurement =
                    `${indicator.value} ${units[key] || ""}`;
            }

            alerts.push({
                state,
                label: labels[key] || key,
                measurement,
                reason: indicator.reason || "Revisar medición."
            });
        }
    );

    if (!alerts.length) {
        const message = document.createElement("p");

        message.className = "alert-item normal";
        message.textContent =
            "No hay alertas en las mediciones clasificadas.";

        container.appendChild(message);
        return;
    }

    alerts.forEach(alert => {
        const item = document.createElement("div");

        item.className =
            "alert-item " + alert.state;

        const title = document.createElement("strong");

        title.textContent =
            `${alert.state.toUpperCase()} — ${alert.label}`;

        const measurement = document.createElement("p");

        measurement.textContent = alert.measurement;

        const reason = document.createElement("p");

        reason.textContent = alert.reason;

        item.appendChild(title);

        if (alert.measurement) {
            item.appendChild(measurement);
        }

        item.appendChild(reason);

        container.appendChild(item);
    });
}

// --------------------------------------------------
// DISPOSITIVO
// --------------------------------------------------

function updateDevice(data) {
    setText("device-id", data.device_id || "UNKNOWN");

    setText("device-state", "RECEIVING DATA");

    if (data.timestamp) {
        setText(
            "last-update",
            new Date(data.timestamp).toLocaleTimeString()
        );
    } else {
        setText("last-update", "--");
    }
}

// --------------------------------------------------
// ACTUALIZACIÓN DE MEDICIONES
// --------------------------------------------------

function updateMeasurement(data) {
    const analysis = getAnalysis(data);

    fields.forEach(field => {
        setIndicator(
            field,
            data[field.key],
            analysis
        );
    });

    updatePressure(data, analysis);
    updateOverall(analysis);
    updateAlerts(analysis);
    updateDevice(data);
}

// --------------------------------------------------
// GRÁFICAS
// --------------------------------------------------

function createChart(canvasId, label, color) {
    const canvas = document.getElementById(canvasId);

    if (!canvas) return;

    chartInstances[canvasId] = new Chart(canvas, {
        type: "line",

        data: {
            labels: [],

            datasets: [{
                label,
                data: [],
                borderColor: color,
                backgroundColor: color + "22",
                borderWidth: 2,
                fill: true,
                tension: 0.3,
                pointRadius: 2,
                spanGaps: false
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: false,

            plugins: {
                legend: {
                    labels: {
                        color: "#8493aa"
                    }
                }
            },

            scales: {
                x: {
                    ticks: {
                        color: "#8493aa"
                    },
                    grid: {
                        color: "#26354d"
                    }
                },

                y: {
                    ticks: {
                        color: "#8493aa"
                    },
                    grid: {
                        color: "#26354d"
                    }
                }
            }
        }
    });
}

function updateCharts(history) {
    const configurations = [
        ["heart-chart", "heart_rate"],
        ["spo2-chart", "spo2"],
        ["temperature-chart", "body_temperature"]
    ];

    configurations.forEach(([chartId, key]) => {
        const chart = chartInstances[chartId];

        if (!chart) return;

        chart.data.labels = history.map(item =>
            new Date(item.timestamp).toLocaleTimeString()
        );

        chart.data.datasets[0].data =
            history.map(item => item[key] ?? null);

        chart.update();
    });
}

// --------------------------------------------------
// CARGAR DASHBOARD
// --------------------------------------------------

async function loadDashboard() {
    try {
        const response = await fetch("/api/dashboard");

        if (!response.ok) {
            throw new Error("Dashboard API unavailable");
        }

        const result = await response.json();

        if (result.latest) {
            updateMeasurement(result.latest);
        }

        updateCharts(result.history || []);

        const statusResponse = await fetch("/api/status");

        if (statusResponse.ok) {
            const status = await statusResponse.json();

            setText(
                "total-measurements",
                status.total_measurements
            );
        }

    } catch (error) {
        console.error("Dashboard error:", error);
    }
}

// --------------------------------------------------
// SOCKET.IO
// --------------------------------------------------

socket.on("connect", () => {
    setText("connection-state", "WEBSOCKET CONNECTED");

    loadDashboard();
});

socket.on("disconnect", () => {
    setText("connection-state", "WEBSOCKET DISCONNECTED");
    setText("device-state", "CONNECTION LOST");
});

socket.on("telemetry_update", data => {
    updateMeasurement(data);

    // Actualizar historial y gráficas.
    loadDashboard();
});

// --------------------------------------------------
// INICIALIZACIÓN
// --------------------------------------------------

createChart(
    "heart-chart",
    "Heart rate",
    "#37c8e8"
);

createChart(
    "spo2-chart",
    "SpO2",
    "#36d399"
);

createChart(
    "temperature-chart",
    "Temperature",
    "#f4c45e"
);

setInterval(() => {
    setText(
        "mission-clock",
        new Date().toLocaleTimeString()
    );
}, 1000);

loadDashboard();
