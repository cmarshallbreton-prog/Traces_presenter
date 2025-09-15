let currentData = null;
let chartsInstances = {};
let currentStudentTraces = {};
let currentTab = 'numeric';
const TIME_SEGMENTS = 10;
let selectedTraces = {
    numeric: new Set(),
    textual: new Set(),
    boolean: new Set()
};
let globalTimeRange = null;

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('fileInput').addEventListener('change', handleFileUpload);
    document.getElementById('studentSelect').addEventListener('change', onStudentChange);
    
    //Events pour les changements d'onglets
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', switchTab);
    });
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
    
    // Réinitialiser les sélections
    selectedTraces.numeric.clear();
    selectedTraces.textual.clear();
    selectedTraces.boolean.clear();
    
    // Peupler les listes des traces par type
    populateTraceList('numericTraceList', currentStudentTraces.numeric, 'numeric');
    populateTraceList('textualTraceList', currentStudentTraces.textual, 'textual');
    populateTraceList('booleanTraceList', currentStudentTraces.boolean, 'boolean');
    
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

function populateTraceList(listId, traces, category) {
    const listContainer = document.getElementById(listId);
    
    if (!listContainer) {
        console.error(`Element ${listId} not found`);
        return;
    }
    
    const traceNames = [...new Set(traces.map(trace => trace.trace.trace_name))];
    
    if (traceNames.length === 0) {
        listContainer.innerHTML = '<div class="no-traces">Aucune trace disponible</div>';
        return;
    }
    
    listContainer.innerHTML = '';
    //Gestion des checkBoxes
    traceNames.forEach(traceName => {
        const traceItem = document.createElement('div');
        traceItem.className = 'trace-item';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `${category}-${traceName}`;
        checkbox.value = traceName;
        checkbox.addEventListener('change', () => onTraceSelectionChange(category, traceName, checkbox.checked));
        
        const label = document.createElement('label');
        label.htmlFor = checkbox.id;
        label.textContent = traceName;
        
        traceItem.appendChild(checkbox);
        traceItem.appendChild(label);
        listContainer.appendChild(traceItem);
    });
}

function onTraceSelectionChange(category, traceName, isSelected) {
    if (isSelected) {
        selectedTraces[category].add(traceName);
    } else {
        selectedTraces[category].delete(traceName);
    }
    
    updateChart(category);
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
    
    // Mettre à jour le graphique pour l'onglet actuel
    if (tabName === 'numeric' || tabName === 'textual' || tabName === 'boolean') {
        updateChart(tabName);
    }
}

function updateChart(category) {
    const chartTitle = document.getElementById(`${category}ChartTitle`);
    const canvasId = `${category}Chart`;
    
    const selectedTraceNames = Array.from(selectedTraces[category]);
    
    if (selectedTraceNames.length === 0) {
        chartTitle.textContent = 'Aucune trace sélectionnée';
        if (chartsInstances[canvasId]) {
            chartsInstances[canvasId].destroy();
            delete chartsInstances[canvasId];
        }
        return;
    }
    
    if (selectedTraceNames.length === 1) {
        chartTitle.textContent = selectedTraceNames[0];
    } else {
        chartTitle.textContent = `${selectedTraceNames.length} traces sélectionnées`;
    }
    
    createMultiChart(selectedTraceNames, canvasId, category);
}

function createMultiChart(selectedTraceNames, canvasId, category) {
    if (chartsInstances[canvasId]) {
        chartsInstances[canvasId].destroy();
        delete chartsInstances[canvasId];
    }
    
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    // Créer le graphique selon le type de données
    if (category === 'numeric') {
        createMultiNumericChart(selectedTraceNames, canvas, canvasId);
    } else if (category === 'boolean') {
        createMultiBooleanChart(selectedTraceNames, canvas, canvasId);
    } else if (category === 'textual') {
        createMultiTextualChart(selectedTraceNames, canvas, canvasId);
    }
}

function createMultiNumericChart(traceNames, canvas, canvasId) {
    const colors = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#6f42c1', '#fd7e14', '#20c997', '#6c757d'];
    const datasets = [];
    
    traceNames.forEach((traceName, index) => {
        const categoryTraces = currentStudentTraces.numeric;
        const traceData = categoryTraces.filter(trace => trace.trace.trace_name === traceName);
        
        const points = traceData.map(trace => ({
            x: new Date(trace.trace.timestamp),
            y: trace.trace.value
        }));
        
        if (points.length > 0) {
            datasets.push({
                label: traceName,
                data: points,
                backgroundColor: colors[index % colors.length],
                borderColor: colors[index % colors.length],
                pointRadius: 4,
                pointHoverRadius: 6
            });
            
            // Ajouter la moyenne évolutive pour cette trace
            const allTraces = currentData.traces.filter(trace => 
                trace.trace.trace_name === traceName && typeof trace.trace.value === 'number'
            );
            
            if (allTraces.length > 0) {
                const averagePoints = calculateTimeBasedAverage(allTraces);
                
                if (averagePoints.length > 0) {
                    datasets.push({
                        label: `${traceName} (moyenne classe)`,
                        data: averagePoints,
                        backgroundColor: colors[index % colors.length],
                        borderColor: colors[index % colors.length],
                        borderDash: [5, 5],
                        pointRadius: 2,
                        showLine: true,
                        fill: false,
                        tension: 0.3
                    });
                }
            }
        }
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

function createMultiTextualChart(traceNames, canvas, canvasId) {
    const baseColors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#34495e', '#e67e22'];
    const datasets = [];
    
    traceNames.forEach((traceName, traceIndex) => {
        const categoryTraces = currentStudentTraces.textual;
        const traceData = categoryTraces.filter(trace => trace.trace.trace_name === traceName);
        
        const allValues = [...new Set(traceData.map(t => t.trace.value))];
        
        allValues.forEach((value, valueIndex) => {
            const valuePoints = traceData
                .filter(trace => trace.trace.value === value)
                .map(trace => ({
                    x: new Date(trace.trace.timestamp),
                    y: 1 + (traceIndex * 0.1) // Décalage vertical pour éviter la superposition
                }));
            
            const colorIndex = (traceIndex * allValues.length + valueIndex) % baseColors.length;
            
            datasets.push({
                label: `${traceName}: ${value}`,
                data: valuePoints,
                backgroundColor: baseColors[colorIndex],
                borderColor: baseColors[colorIndex],
                pointRadius: 6,
                pointHoverRadius: 6,
                showLine: false
            });
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
                    min: 0.8, max: 2.2,
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

function createMultiBooleanChart(traceNames, canvas, canvasId) {
    const datasets = [];
    
    // Créer un dataset pour les valeurs true et un pour les valeurs false
    const truePoints = [];
    const falsePoints = [];
    
    traceNames.forEach((traceName, traceIndex) => {
        const categoryTraces = currentStudentTraces.boolean;
        const traceData = categoryTraces.filter(trace => trace.trace.trace_name === traceName);
        
        traceData.forEach(trace => {
            const point = {
                x: new Date(trace.trace.timestamp),
                y: traceIndex, // Position exacte sur l'axe Y
                traceName: traceName
            };
            
            if (trace.trace.value === true) {
                truePoints.push(point);
            } else {
                falsePoints.push(point);
            }
        });
    });
    
    // Dataset pour les valeurs true (vert)
    if (truePoints.length > 0) {
        datasets.push({
            label: 'True',
            data: truePoints,
            backgroundColor: '#2ecc71',
            borderColor: '#2ecc71',
            pointRadius: 8,
            pointHoverRadius: 8,
            showLine: false
        });
    }
    
    // Dataset pour les valeurs false (rouge)
    if (falsePoints.length > 0) {
        datasets.push({
            label: 'False',
            data: falsePoints,
            backgroundColor: '#e74c3c',
            borderColor: '#e74c3c',
            pointRadius: 8,
            pointHoverRadius: 8,
            showLine: false
        });
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
                    type: 'linear',
                    min: -0.5,
                    max: traceNames.length - 0.5,
                    ticks: {
                        stepSize: 1,
                        // Forcer les ticks à être exactement aux positions entières
                        callback: function(value, index, ticks) {
                            // Ne montrer que les valeurs entières qui correspondent aux indices des traces
                            if (Number.isInteger(value) && value >= 0 && value < traceNames.length) {
                                return traceNames[value];
                            }
                            return '';
                        },
                        // Forcer l'affichage des ticks aux positions exactes
                        major: {
                            enabled: true
                        }
                    },
                    title: { display: true, text: 'Traces' },
                    grid: {
                        display: true,
                        drawOnChartArea: true,
                        color: function(context) {
                            // Ne montrer les lignes de grille que pour les positions entières
                            if (Number.isInteger(context.tick.value)) {
                                return '#e0e0e0';
                            }
                            return 'transparent';
                        }
                    },
                    // Définir manuellement les ticks pour être sûr de l'alignement
                    afterBuildTicks: function(axis) {
                        axis.ticks = [];
                        for (let i = 0; i < traceNames.length; i++) {
                            axis.ticks.push({
                                value: i,
                                major: true
                            });
                        }
                    }
                }
            },
            plugins: {
                legend: { 
                    display: true, 
                    position: 'top',
                    labels: { usePointStyle: true }
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const date = new Date(context[0].parsed.x);
                            return date.toLocaleString('fr-FR');
                        },
                        label: function(context) {
                            const traceIndex = Math.round(context.parsed.y);
                            const traceName = traceNames[traceIndex];
                            const value = context.dataset.label;
                            return `${traceName}: ${value}`;
                        }
                    }
                }
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