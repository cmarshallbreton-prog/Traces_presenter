// CONSTANTES
const TIME_SEGMENTS = 10;
const TRACE_COLORS = [
    '#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', 
    '#1abc9c', '#34495e', '#e67e22', '#95a5a6', '#c0392b',
    '#2980b9', '#27ae60', '#d68910', '#8e44ad', '#16a085'
];
const CHART_COLORS = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#6f42c1', '#fd7e14', '#20c997', '#6c757d'];
const BOOLEAN_COLORS = { TRUE: '#2ecc71', FALSE: '#e74c3c' };

// NAVIGATION
const state = {
    currentData: null,
    chartsInstances: {},
    currentStudentTraces: {},
    currentTab: 'numeric',
    selectedTraces: {
        numeric: new Set(),
        textual: new Set(),
        boolean: new Set()
    },
    globalTimeRange: null
};

// UTILS
const DOM = {
    cache: {},
    get(id) {
        if (!this.cache[id]) {
            this.cache[id] = document.getElementById(id);
        }
        return this.cache[id];
    },
    setText(id, text) {
        const element = this.get(id);
        if (element) element.textContent = text;
    },
    setHTML(id, html) {
        const element = this.get(id);
        if (element) element.innerHTML = html;
    },
    show(id) {
        const element = this.get(id);
        if (element) element.style.display = 'block';
    },
    hide(id) {
        const element = this.get(id);
        if (element) element.style.display = 'none';
    }
};

// INIT
document.addEventListener('DOMContentLoaded', () => {
    DOM.get('fileInput')?.addEventListener('change', handleFileUpload);
    DOM.get('studentSelect')?.addEventListener('change', onStudentChange);
    
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', switchTab);
    });
});

// GESTION DU FICHIER JSON
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    DOM.setHTML('fileInfo', `<div class="loading"></div> Analyse de ${file.name}...`);

    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const data = JSON.parse(e.target.result);
            state.currentData = data;
            calculateGlobalTimeRange(data);
            displayProjectInfo(data);
            populateStudentDropdown(data);
            DOM.setHTML('fileInfo', `✅ Fichier "${file.name}" chargé avec succès`);
            DOM.hide('upload-section');
        } catch (error) {
            showError('Erreur lors du chargement du fichier JSON: ' + error.message);
            DOM.setHTML('fileInfo', '');
        }
    };

    reader.onerror = () => {
        showError('Erreur lors de la lecture du fichier');
        DOM.setHTML('fileInfo', '');
    };

    reader.readAsText(file);
}

function calculateGlobalTimeRange(data) {
    const allTimestamps = data.traces.map(trace => new Date(trace.trace.timestamp));
    state.globalTimeRange = {
        min: new Date(Math.min(...allTimestamps)),
        max: new Date(Math.max(...allTimestamps))
    };
}

// METADONNEES
function displayProjectInfo(data) {
    const { metadata, traces } = data;
    const uniqueStudents = new Set(traces.map(trace => trace.student_id));
    
    DOM.setText('projectTitle', metadata.project_name || 'Projet sans nom');
    DOM.setText('projectDescription', metadata.description || 'Aucune description disponible');
    DOM.setText('totalTraces', `${traces.length} traces`);
    DOM.setText('totalStudents', `${uniqueStudents.size} étudiants`);
    DOM.show('projectInfo');
}

// LISTE DES ETUDIANTS
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
    
    const students = Array.from(studentsMap.values())
        .sort((a, b) => a.name.localeCompare(b.name));
    
    const studentSelect = DOM.get('studentSelect');
    if (studentSelect) {
        studentSelect.innerHTML = '<option value="">-- Choisir un étudiant --</option>';
        
        students.forEach(student => {
            const option = document.createElement('option');
            option.value = student.id;
            option.textContent = student.name;
            studentSelect.appendChild(option);
        });
    }
    
    DOM.show('studentSelector');
}

function onStudentChange() {
    hideError();
    
    const selectedStudentId = DOM.get('studentSelect')?.value;
    
    if (!selectedStudentId || !state.currentData) {
        DOM.hide('studentDashboard');
        return;
    }
    
    const studentTraces = state.currentData.traces.filter(trace => 
        trace.student_id === selectedStudentId
    );
    const selectedStudent = studentTraces[0];
    
    if (!selectedStudent) {
        showError('Étudiant non trouvé');
        return;
    }
    
    displayStudentDashboard(selectedStudent.student_name, studentTraces);
}

// DASHBOARD DE L'ETUDIANT
function displayStudentDashboard(studentName, studentTraces) {
    DOM.setText('selectedStudentName', `Étudiant : ${studentName}`);
    
    // Clean up 
    Object.values(state.chartsInstances).forEach(chart => chart?.destroy?.());
    state.chartsInstances = {};
    
    // Reset de la navigation
    Object.keys(state.selectedTraces).forEach(key => {
        state.selectedTraces[key].clear();
    });
    
    // Categorisation des traces
    state.currentStudentTraces = categorizeTracesByType(studentTraces);
    
    // Liste de traces
    populateTraceList('numericTraceList', state.currentStudentTraces.numeric, 'numeric');
    populateTraceList('textualTraceList', state.currentStudentTraces.textual, 'textual');
    populateTraceList('booleanTraceList', state.currentStudentTraces.boolean, 'boolean');
    
    // Tableau 'autres'
    generateTable('othersTable', state.currentStudentTraces.others);
    
    switchToTab(state.currentTab);
    DOM.show('studentDashboard');
}

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
        } else {
            const type = typeof value;
            categorized[type === 'number' ? 'numeric' : 
                     type === 'boolean' ? 'boolean' : 
                     type === 'string' ? 'textual' : 'others'].push(trace);
        }
    });
    
    return categorized;
}

// GESTION DES TRACES
function populateTraceList(listId, traces, category) {
    const listContainer = DOM.get(listId);
    if (!listContainer) return;
    
    const traceNames = [...new Set(traces.map(trace => trace.trace.trace_name))];
    
    if (traceNames.length === 0) {
        listContainer.innerHTML = '<div class="no-traces">Aucune trace disponible</div>';
        return;
    }
    
    listContainer.innerHTML = traceNames.map(traceName => 
        `<div class="trace-item">
            <input type="checkbox" 
                   id="${category}-${traceName}" 
                   value="${traceName}"
                   onchange="onTraceSelectionChange('${category}', '${traceName}', this.checked)">
            <label for="${category}-${traceName}">${traceName}</label>
        </div>`
    ).join('');
}

function onTraceSelectionChange(category, traceName, isSelected) {
    if (isSelected) {
        state.selectedTraces[category].add(traceName);
    } else {
        state.selectedTraces[category].delete(traceName);
    }
    
    if (category === 'textual') {
        updateTextualTable();
    } else {
        updateChart(category);
    }
}

// BOUTON SELECT ALL
function selectAllTraces(category) {
    const checkboxes = document.querySelectorAll(`#${category}TraceList input[type="checkbox"]`);
    
    checkboxes.forEach(checkbox => {
        if (!checkbox.checked) {
            checkbox.checked = true;
            state.selectedTraces[category].add(checkbox.value);
        }
    });
    
    // Update
    if (category === 'textual') {
        updateTextualTable();
    } else {
        updateChart(category);
    }
}

function deselectAllTraces(category) {
    const checkboxes = document.querySelectorAll(`#${category}TraceList input[type="checkbox"]`);
    
    checkboxes.forEach(checkbox => {
        if (checkbox.checked) {
            checkbox.checked = false;
            state.selectedTraces[category].delete(checkbox.value);
        }
    });
    
    // Update
    if (category === 'textual') {
        updateTextualTable();
    } else {
        updateChart(category);
    }
}

// GESTION DES ONGLETS
function switchTab(event) {
    const targetTab = event.target.dataset.tab;
    state.currentTab = targetTab;
    switchToTab(targetTab);
}

function switchToTab(tabName) {
    state.currentTab = tabName;
    
    // Update boutons onglets
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Update contenu de l'onglet
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    DOM.get(tabName + 'Tab')?.classList.add('active');
    
    // Update display based on tab
    if (tabName === 'textual') {
        updateTextualTable();
    } else if (['numeric', 'boolean'].includes(tabName)) {
        updateChart(tabName);
    }
}

// GESTION DES GRAPHES
function updateChart(category) {
    const selectedTraceNames = Array.from(state.selectedTraces[category]);
    const titleElement = DOM.get(`${category}ChartTitle`);
    
    if (!titleElement) return;
    
    if (selectedTraceNames.length === 0) {
        titleElement.textContent = 'Aucune trace sélectionnée';
        destroyChart(`${category}Chart`);
        return;
    }
    
    titleElement.textContent = selectedTraceNames.length === 1 
        ? selectedTraceNames[0] 
        : `${selectedTraceNames.length} traces sélectionnées`;
    
    createChart(selectedTraceNames, `${category}Chart`, category);
}

function destroyChart(canvasId) {
    if (state.chartsInstances[canvasId]) {
        state.chartsInstances[canvasId].destroy();
        delete state.chartsInstances[canvasId];
    }
}

function createChart(traceNames, canvasId, category) {
    destroyChart(canvasId);
    
    const canvas = DOM.get(canvasId);
    if (!canvas) return;
    
    const chartCreators = {
        numeric: createNumericChart,
        boolean: createBooleanChart
    };
    
    chartCreators[category]?.(traceNames, canvas, canvasId);
}

function createNumericChart(traceNames, canvas, canvasId) {
    const datasets = [];
    
    traceNames.forEach((traceName, index) => {
        const traceData = state.currentStudentTraces.numeric
            .filter(trace => trace.trace.trace_name === traceName);
        
        const points = traceData.map(trace => ({
            x: new Date(trace.trace.timestamp),
            y: trace.trace.value
        }));
        
        if (points.length > 0) {
            const color = CHART_COLORS[index % CHART_COLORS.length];
            
            datasets.push({
                label: traceName,
                data: points,
                backgroundColor: color,
                borderColor: color,
                pointRadius: 4,
                pointHoverRadius: 6
            });
            
            // Moyenne
            const classAverage = calculateClassAverage(traceName);
            if (classAverage.length > 0) {
                datasets.push({
                    label: `${traceName} (moyenne classe)`,
                    data: classAverage,
                    backgroundColor: '#f8f9fa',
                    borderColor: color,
                    borderDash: [5, 5],
                    pointRadius: 2,
                    showLine: true,
                    fill: false,
                    tension: 0.3
                });
            }
        }
    });
    
    createChartInstance(canvas, canvasId, 'scatter', datasets, getNumericChartOptions());
}

function createBooleanChart(traceNames, canvas, canvasId) {
    const truePoints = [];
    const falsePoints = [];
    
    traceNames.forEach((traceName, traceIndex) => {
        const traceData = state.currentStudentTraces.boolean
            .filter(trace => trace.trace.trace_name === traceName);
        
        traceData.forEach(trace => {
            const point = {
                x: new Date(trace.trace.timestamp),
                y: traceIndex,
                traceName: traceName
            };
            
            (trace.trace.value ? truePoints : falsePoints).push(point);
        });
    });
    
    const datasets = [];
    if (truePoints.length > 0) {
        datasets.push({
            label: 'True',
            data: truePoints,
            backgroundColor: BOOLEAN_COLORS.TRUE,
            borderColor: BOOLEAN_COLORS.TRUE,
            pointRadius: 8,
            pointHoverRadius: 8,
            showLine: false
        });
    }
    
    if (falsePoints.length > 0) {
        datasets.push({
            label: 'False',
            data: falsePoints,
            backgroundColor: BOOLEAN_COLORS.FALSE,
            borderColor: BOOLEAN_COLORS.FALSE,
            pointRadius: 8,
            pointHoverRadius: 8,
            showLine: false
        });
    }
    
    createChartInstance(canvas, canvasId, 'scatter', datasets, getBooleanChartOptions(traceNames));
}

function createChartInstance(canvas, canvasId, type, datasets, options) {
    const ctx = canvas.getContext('2d');
    state.chartsInstances[canvasId] = new Chart(ctx, {
        type,
        data: { datasets },
        options
    });
}

function getNumericChartOptions() {
    return {
        responsive: true,
        animation: false,
        scales: {
            x: {
                type: 'time',
                time: {
                    unit: 'minute',
                    displayFormats: { minute: 'HH:mm' }
                },
                title: { display: true, text: 'Temps' },
                min: state.globalTimeRange.min,
                max: state.globalTimeRange.max
            },
            y: {
                beginAtZero: true,
                title: { display: true, text: 'Valeur' }
            }
        },
        plugins: {
            legend: { display: true, position: 'top' }
        }
    };
}

function getBooleanChartOptions(traceNames) {
    return {
        responsive: true,
        animation: false,
        scales: {
            x: {
                type: 'time',
                time: {
                    unit: 'minute',
                    displayFormats: { minute: 'HH:mm' }
                },
                title: { display: true, text: 'Temps' },
                min: state.globalTimeRange.min,
                max: state.globalTimeRange.max
            },
            y: {
                type: 'linear',
                min: -0.5,
                max: traceNames.length - 0.5,
                ticks: {
                    stepSize: 1,
                    callback: function(value, index, ticks) {
                        if (Number.isInteger(value) && value >= 0 && value < traceNames.length) {
                            return traceNames[value];
                        }
                        return '';
                    },
                    major: {
                        enabled: true
                    }
                },
                title: { display: true, text: 'Traces' },
                grid: {
                    display: true,
                    drawOnChartArea: true,
                    color: function(context) {
                        if (Number.isInteger(context.tick.value)) {
                            return '#e0e0e0';
                        }
                        return 'transparent';
                    }
                },
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
            legend: { display: true, position: 'top', labels: { usePointStyle: true } },
            tooltip: {
                callbacks: {
                    title: function(context) {
                        return new Date(context[0].parsed.x).toLocaleString('fr-FR');
                    },
                    label: function(context) {
                        const traceIndex = Math.round(context.parsed.y);
                        return `${traceNames[traceIndex]}: ${context.dataset.label}`;
                    }
                }
            }
        }
    };
}

// TABLEAU DONNESS TEXTE
function updateTextualTable() {
    const selectedTraceNames = Array.from(state.selectedTraces.textual);
    
    if (selectedTraceNames.length === 0) {
        DOM.setText('textualTableTitle', 'Aucune trace sélectionnée');
        DOM.setHTML('textualTable', '<div class="no-data">Sélectionnez des traces à afficher</div>');
        return;
    }
    
    DOM.setText('textualTableTitle', 
        selectedTraceNames.length === 1 
            ? selectedTraceNames[0] 
            : `${selectedTraceNames.length} traces sélectionnées`
    );
    
    generateTextualTable(selectedTraceNames);
}

function generateTextualTable(selectedTraceNames) {
    const selectedTraces = state.currentStudentTraces.textual
        .filter(trace => selectedTraceNames.includes(trace.trace.trace_name))
        .sort((a, b) => new Date(a.trace.timestamp) - new Date(b.trace.timestamp));
    
    if (selectedTraces.length === 0) {
        DOM.setHTML('textualTable', '<div class="no-data">Aucune trace disponible</div>');
        return;
    }
    
    const colorMap = new Map();
    selectedTraceNames.forEach((name, index) => {
        colorMap.set(name, TRACE_COLORS[index % TRACE_COLORS.length]);
    });
    
    const rows = selectedTraces.map(trace => {
        const timestamp = new Date(trace.trace.timestamp).toLocaleString('fr-FR');
        const color = colorMap.get(trace.trace.trace_name);
        
        return `
            <tr>
                <td>${timestamp}</td>
                <td>
                    <span class="trace-badge" style="background-color: ${color};">
                        ${trace.trace.trace_name}
                    </span>
                </td>
                <td>
                    <div class="trace-value" style="border-left-color: ${color};">
                        ${trace.trace.value || '-'}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
    
    DOM.setHTML('textualTable', `
        <div class="table-responsive">
            <table>
                <thead>
                    <tr>
                        <th>Horodatage</th>
                        <th>Type de trace</th>
                        <th>Valeur</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `);
}

// UTILS
function calculateClassAverage(traceName) {
    const allTraces = state.currentData.traces.filter(trace => 
        trace.trace.trace_name === traceName && typeof trace.trace.value === 'number'
    );
    
    if (allTraces.length === 0) return [];
    
    const totalDuration = state.globalTimeRange.max.getTime() - state.globalTimeRange.min.getTime();
    const segmentDuration = totalDuration / TIME_SEGMENTS;
    const averagePoints = [];
    
    for (let i = 0; i < TIME_SEGMENTS; i++) {
        const segmentStart = new Date(state.globalTimeRange.min.getTime() + (i * segmentDuration));
        const segmentEnd = new Date(state.globalTimeRange.min.getTime() + ((i + 1) * segmentDuration));
        const segmentMiddle = new Date(state.globalTimeRange.min.getTime() + ((i + 0.5) * segmentDuration));
        
        const tracesInSegment = allTraces.filter(trace => {
            const traceTime = new Date(trace.trace.timestamp);
            return traceTime >= segmentStart && traceTime < segmentEnd;
        });
        
        if (tracesInSegment.length > 0) {
            const average = tracesInSegment.reduce((sum, trace) => sum + trace.trace.value, 0) / tracesInSegment.length;
            averagePoints.push({ x: segmentMiddle, y: average });
        }
    }
    
    return averagePoints;
}

function generateTable(tableId, traces) {
    if (traces.length === 0) {
        DOM.setHTML(tableId, '<div class="no-data">Aucune trace pour cet étudiant</div>');
        return;
    }
    
    const sortedTraces = traces.sort((a, b) => 
        new Date(a.trace.timestamp) - new Date(b.trace.timestamp)
    );
    
    const rows = sortedTraces.map(trace => `
        <tr>
            <td>${new Date(trace.trace.timestamp).toLocaleString('fr-FR')}</td>
            <td>${trace.trace.trace_name}</td>
            <td>${trace.trace.value !== undefined ? trace.trace.value : '-'}</td>
        </tr>
    `).join('');
    
    DOM.setHTML(tableId, `
        <div class="table-responsive">
            <table>
                <thead>
                    <tr>
                        <th>Horodatage</th>
                        <th>Type de trace</th>
                        <th>Valeur</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `);
}

// ERREURS
function showError(message) {
    DOM.setText('errorMessage', message);
    DOM.show('errorMessage');
    ['projectInfo', 'studentSelector', 'studentDashboard'].forEach(DOM.hide);
}

function hideError() {
    DOM.hide('errorMessage');
}