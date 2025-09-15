let currentData = null;
let chartsInstances = {};
let currentStudentTraces = {};
let currentTab = 'numeric';
const TIME_SEGMENTS = 10;
let selectedTraces = {
    numeric: null,
    textual: null,
    boolean: null
};
let globalTimeRange = null;

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('fileInput').addEventListener('change', handleFileUpload);
    document.getElementById('studentSelect').addEventListener('change', onStudentChange);
    
    //Events pour les changements d'onglets
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', switchTab);
    });
    
    //Events pour la sélection des onglets à graphes
    document.getElementById('numericTraceSelect').addEventListener('change', () => updateChart('numeric'));
    document.getElementById('textualTraceSelect').addEventListener('change', () => updateChart('textual'));
    document.getElementById('booleanTraceSelect').addEventListener('change', () => updateChart('boolean'));
});

function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const fileInfo = document.getElementById('fileInfo');
    fileInfo.innerHTML = `<div class="loading"></div> Analyse de ${file.name}...`;

    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const data = JSON.parse(e.target.result);
            currentData = data;
            calculateGlobalTimeRange(data);
            displayProjectInfo(data);
            populateStudentDropdown(data);
            fileInfo.innerHTML = `✅ Fichier "${file.name}" chargé avec succès`;
        } catch (error) {
            showError('Erreur lors du chargement du fichier JSON: ' + error.message);
            fileInfo.innerHTML = '';
        }
    };

    reader.onerror = function() {
        showError('Erreur lors de la lecture du fichier');
        fileInfo.innerHTML = '';
    };

    reader.readAsText(file);
}

function calculateGlobalTimeRange(data) {
    const allTimestamps = data.traces.map(trace => new Date(trace.trace.timestamp));
    globalTimeRange = {
        min: new Date(Math.min(...allTimestamps)),
        max: new Date(Math.max(...allTimestamps))
    };
}

function displayProjectInfo(data) {
    const metadata = data.metadata;
    const traces = data.traces;
    
    document.getElementById('projectTitle').textContent = metadata.project_name || 'Projet sans nom';
    document.getElementById('projectDescription').textContent = metadata.description || 'Aucune description disponible';
    
    const uniqueStudents = new Set(traces.map(trace => trace.student_id));
    document.getElementById('totalTraces').textContent = `${traces.length} traces`;
    document.getElementById('totalStudents').textContent = `${uniqueStudents.size} étudiants`;
    
    document.getElementById('projectInfo').style.display = 'block';
}

function populateStudentDropdown(data) {
    const studentsMap = new Map();
    
    data.traces.forEach(trace => {
        if (!studentsMap.has(trace.student_id)) {
            studentsMap.set(trace.student_id, {
                id: trace.student_id,
                name: trace.student_name
            });
        }
    });
    
    const students = Array.from(studentsMap.values()).sort((a, b) => a.name.localeCompare(b.name));
    
    const studentSelect = document.getElementById('studentSelect');
    studentSelect.innerHTML = '<option value="">-- Choisir un étudiant --</option>';
    
    students.forEach(student => {
        const option = document.createElement('option');
        option.value = student.id;
        option.textContent = student.name;
        studentSelect.appendChild(option);
    });
    
    document.getElementById('studentSelector').style.display = 'block';
}

function onStudentChange() {
    hideError();
    
    const studentSelect = document.getElementById('studentSelect');
    const selectedStudentId = studentSelect.value;
    
    if (!selectedStudentId || !currentData) {
        document.getElementById('studentDashboard').style.display = 'none';
        return;
    }
    
    const selectedStudent = currentData.traces.find(trace => trace.student_id === selectedStudentId);
    const studentTraces = currentData.traces.filter(trace => trace.student_id === selectedStudentId);
    
    if (!selectedStudent) {
        showError('Étudiant non trouvé');
        return;
    }
    
    displayStudentDashboard(selectedStudent.student_name, studentTraces);
}

function displayStudentDashboard(studentName, studentTraces) {
    document.getElementById('selectedStudentName').textContent = `Étudiant : ${studentName}`;
    
    // Catégoriser les traces selon le type de données
    currentStudentTraces = categorizeTracesByType(studentTraces);
    
    // Suppression des anciens graphiques
    Object.values(chartsInstances).forEach(chart => {
        if (chart && typeof chart.destroy === 'function') {
            chart.destroy();
        }
    });
    chartsInstances = {};
    
    // Peupler les dropdowns des traces par type
    populateTraceDropdown('numericTraceSelect', currentStudentTraces.numeric);
    populateTraceDropdown('textualTraceSelect', currentStudentTraces.textual);
    populateTraceDropdown('booleanTraceSelect', currentStudentTraces.boolean);
    
    // Générer le tableau pour les autres traces
    generateTable('othersTable', currentStudentTraces.others);
    
    switchToTab(currentTab);
    
    document.getElementById('studentDashboard').style.display = 'block';
}

// Nouvelle fonction pour catégoriser selon le type de données
function categorizeTracesByType(traces) {
    const categorized = {
        numeric: [],
        textual: [],
        boolean: [],
        others: []
    };
    
    traces.forEach(trace => {
        const value = trace.trace.value;
        
        if (value === undefined || value === null) {
            categorized.others.push(trace);
        } else if (typeof value === 'number') {
            categorized.numeric.push(trace);
        } else if (typeof value === 'boolean') {
            categorized.boolean.push(trace);
        } else if (typeof value === 'string') {
            categorized.textual.push(trace);
        } else {
            categorized.others.push(trace);
        }
    });
    
    return categorized;
}

function populateTraceDropdown(selectId, traces) {
    const select = document.getElementById(selectId);
    
    if (!select) {
        console.error(`Element ${selectId} not found`);
        return;
    }
    
    const traceNames = [...new Set(traces.map(trace => trace.trace.trace_name))];
    
    if (traceNames.length === 0) {
        select.innerHTML = '<option value="">-- Aucune trace disponible --</option>';
        return;
    }
    
    select.innerHTML = '';
    
    const category = selectId.replace('TraceSelect', '');
    let selectedTrace = null;
    
    if (selectedTraces[category] && traceNames.includes(selectedTraces[category])) {
        selectedTrace = selectedTraces[category];
    } else {
        selectedTrace = traceNames[0];
        selectedTraces[category] = selectedTrace;
    }
    
    traceNames.forEach(traceName => {
        const option = document.createElement('option');
        option.value = traceName;
        option.textContent = traceName;
        if (traceName === selectedTrace) {
            option.selected = true;
        }
        select.appendChild(option);
    });
    
    if (category === currentTab) {
        updateChart(category);
    }
}

function switchTab(event) {
    const targetTab = event.target.dataset.tab;
    currentTab = targetTab;
    switchToTab(targetTab);
}

function switchToTab(tabName) {
    currentTab = tabName;
    // active pour display, cf css.
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active');
        }
    });
    
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    const targetTab = document.getElementById(tabName + 'Tab');
    if (targetTab) {
        targetTab.classList.add('active');
    }
    
    if (tabName === 'numeric' || tabName === 'textual' || tabName === 'boolean') {
        const select = document.getElementById(tabName + 'TraceSelect');
        if (select && select.value) {
            updateChart(tabName);
        }
    }
}

function updateChart(category) {
    const traceSelect = document.getElementById(`${category}TraceSelect`);
    const chartTitle = document.getElementById(`${category}ChartTitle`);
    const canvasId = `${category}Chart`;
    
    const selectedTrace = traceSelect.value;
    
    if (!selectedTrace) {
        chartTitle.textContent = 'Aucune trace disponible';
        if (chartsInstances[canvasId]) {
            chartsInstances[canvasId].destroy();
            delete chartsInstances[canvasId];
        }
        return;
    }
    
    selectedTraces[category] = selectedTrace;
    
    const categoryTraces = currentStudentTraces[category];
    const selectedTraces_data = categoryTraces.filter(trace => trace.trace.trace_name === selectedTrace);
    
    chartTitle.textContent = `${selectedTrace}`;
    
    createChart(selectedTraces_data, canvasId, category, selectedTrace);
}

function createChart(studentTraces, canvasId, category, traceName) {
    if (chartsInstances[canvasId]) {
        chartsInstances[canvasId].destroy();
        delete chartsInstances[canvasId];
    }
    
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    // Obtenir toutes les traces de même nom pour calculer la moyenne
    const allTraces = currentData.traces.filter(trace => trace.trace.trace_name === traceName);
    
    const sortedStudentTraces = studentTraces.sort((a, b) => 
        new Date(a.trace.timestamp) - new Date(b.trace.timestamp)
    );
    
    if (sortedStudentTraces.length === 0) {
        const container = canvas.parentElement;
        const titleElement = container.querySelector('h4');
        if (titleElement) {
            titleElement.textContent = 'Aucune donnée pour cette trace';
        }
        return;
    }
    
    // Créer le graphique selon le type de données
    if (category === 'numeric') {
        createNumericChart(sortedStudentTraces, allTraces, canvas, canvasId);
    } else if (category === 'boolean') {
        createBooleanChart(sortedStudentTraces, canvas, canvasId);
    } else if (category === 'textual') {
        createTextualChart(sortedStudentTraces, canvas, canvasId);
    }
}

function createNumericChart(studentTraces, allTraces, canvas, canvasId) {
    const points = studentTraces.map(trace => ({
        x: new Date(trace.trace.timestamp),
        y: trace.trace.value
    }));
    
    const datasets = [{
        label: 'Étudiant',
        data: points,
        backgroundColor: '#007bff',
        borderColor: '#007bff',
        pointRadius: 4,
        pointHoverRadius: 6
    }];
    
    // Calculer la moyenne évolutive en TIME_SEGMENTS segments
    const allNumericTraces = allTraces.filter(t => typeof t.trace.value === 'number');
    if (allNumericTraces.length > 0) {
        const averagePoints = calculateTimeBasedAverage(allNumericTraces);
        
        if (averagePoints.length > 0) {
            datasets.push({
                label: 'Moyenne classe (évolutive)',
                data: averagePoints,
                backgroundColor: '#dc3545',
                borderColor: '#dc3545',
                borderDash: [5, 5],
                pointRadius: 3,
                showLine: true,
                fill: false,
                tension: 0.3
            });
        }
    }
    
    const ctx = canvas.getContext('2d');
    chartsInstances[canvasId] = new Chart(ctx, {
        type: 'scatter',
        data: { datasets },
        options: {
            responsive: true,
            animation: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        displayFormats: {
                            minute: 'HH:mm'
                        }
                    },
                    title: { display: true, text: 'Temps' },
                    min: globalTimeRange.min,
                    max: globalTimeRange.max
                },
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Valeur' }
                }
            },
            plugins: {
                legend: { display: true, position: 'top' }
            }
        }
    });
}

// Calcul des intervals de temps pour la moyenne évolutive
function calculateTimeBasedAverage(allNumericTraces) {
    const totalDuration = globalTimeRange.max.getTime() - globalTimeRange.min.getTime();
    const segmentDuration = totalDuration / TIME_SEGMENTS; // Diviser en TIME_SEGMENTS segments
    
    const averagePoints = [];
    
    for (let i = 0; i < TIME_SEGMENTS; i++) {
        const segmentStart = new Date(globalTimeRange.min.getTime() + (i * segmentDuration));
        const segmentEnd = new Date(globalTimeRange.min.getTime() + ((i + 1) * segmentDuration));
        const segmentMiddle = new Date(globalTimeRange.min.getTime() + ((i + 0.5) * segmentDuration));
        
        // Filtrer les traces qui tombent dans ce segment
        const tracesInSegment = allNumericTraces.filter(trace => {
            const traceTime = new Date(trace.trace.timestamp);
            return traceTime >= segmentStart && traceTime < segmentEnd;
        });
        
        // Calculer la moyenne pour ce segment s'il y a des données
        if (tracesInSegment.length > 0) {
            const values = tracesInSegment.map(t => t.trace.value);
            const average = values.reduce((sum, val) => sum + val, 0) / values.length;
            
            averagePoints.push({
                x: segmentMiddle,
                y: average
            });
        }
    }
    
    return averagePoints;
}

function createTextualChart(studentTraces, canvas, canvasId) {
    const allValues = [...new Set(studentTraces.map(t => t.trace.value))];
    const colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c'];
    const colorMap = {};
    
    allValues.forEach((value, index) => {
        colorMap[value] = colors[index % colors.length];
    });

    const datasets = [];
    allValues.forEach(value => {
        const valuePoints = studentTraces
            .filter(trace => trace.trace.value === value)
            .map(trace => ({
                x: new Date(trace.trace.timestamp),
                y: 1
            }));
        
        datasets.push({
            label: value.toString(),
            data: valuePoints,
            backgroundColor: colorMap[value],
            borderColor: colorMap[value],
            pointRadius: 8,
            showLine: false
        });
    });
    
    const ctx = canvas.getContext('2d');
    chartsInstances[canvasId] = new Chart(ctx, {
        type: 'scatter',
        data: { datasets },
        options: {
            responsive: true,
            animation: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        displayFormats: {
                            minute: 'HH:mm'
                        }
                    },
                    title: { display: true, text: 'Temps' },
                    min: globalTimeRange.min,
                    max: globalTimeRange.max
                },
                y: {
                    min: 0.5, max: 1.5,
                    ticks: { display: false },
                    grid: { display: false },
                    title: { display: false }
                }
            },
            plugins: {
                legend: { display: true, position: 'top', labels: { usePointStyle: true } }
            }
        }
    });
}

function createBooleanChart(studentTraces, canvas, canvasId) {
    const allValues = [...new Set(studentTraces.map(t => t.trace.value))];
    const colorMap = {};
    
    colorMap[true] = '#2ecc71';
    colorMap[false] = '#e74c3c';

    const datasets = [];
    allValues.forEach(value => {
        const valuePoints = studentTraces
            .filter(trace => trace.trace.value === value)
            .map(trace => ({
                x: new Date(trace.trace.timestamp),
                y: 1
            }));
        
        datasets.push({
            label: value.toString(),
            data: valuePoints,
            backgroundColor: colorMap[value],
            borderColor: colorMap[value],
            pointRadius: 8,
            showLine: false
        });
    });
    
    const ctx = canvas.getContext('2d');
    chartsInstances[canvasId] = new Chart(ctx, {
        type: 'scatter',
        data: { datasets },
        options: {
            responsive: true,
            animation: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'minute',
                        displayFormats: {
                            minute: 'HH:mm'
                        }
                    },
                    title: { display: true, text: 'Temps' },
                    min: globalTimeRange.min,
                    max: globalTimeRange.max
                },
                y: {
                    min: 0.5, max: 1.5,
                    ticks: { display: false },
                    grid: { display: false },
                    title: { display: false }
                }
            },
            plugins: {
                legend: { display: true, position: 'top', labels: { usePointStyle: true } }
            }
        }
    });
}

function generateTable(tableId, traces) {
    const tableContainer = document.getElementById(tableId);
    
    if (!tableContainer) {
        console.error(`Element ${tableId} not found`);
        return;
    }
    
    if (traces.length === 0) {
        tableContainer.innerHTML = '<div class="no-data">Aucune trace pour cet étudiant</div>';
        return;
    }
    
    let tableHtml = `
        <div class="table-responsive">
            <table>
                <thead>
                    <tr>
                        <th>Horodatage</th>
                        <th>Type de trace</th>
                        <th>Valeur</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    const sortedTraces = traces.sort((a, b) => 
        new Date(a.trace.timestamp) - new Date(b.trace.timestamp)
    );
    
    sortedTraces.forEach(trace => {
        const timestamp = new Date(trace.trace.timestamp).toLocaleString('fr-FR');
        const value = trace.trace.value !== undefined ? trace.trace.value : '-';
        
        tableHtml += `
            <tr>
                <td>${timestamp}</td>
                <td>${trace.trace.trace_name}</td>
                <td>${value}</td>
            </tr>
        `;
    });
    
    tableHtml += `
                </tbody>
            </table>
        </div>
    `;
    
    tableContainer.innerHTML = tableHtml;
}

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    document.getElementById('projectInfo').style.display = 'none';
    document.getElementById('studentSelector').style.display = 'none';
    document.getElementById('studentDashboard').style.display = 'none';
}

function hideError() {
    document.getElementById('errorMessage').style.display = 'none';
}