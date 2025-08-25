let currentData = null;
let chartsInstances = {};
let currentStudentTraces = {};
let currentTab = 'static';
let selectedTraces = {
    static: null,
    dynamic: null
};

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('fileInput').addEventListener('change', handleFileUpload);
    document.getElementById('studentSelect').addEventListener('change', onStudentChange);
    
    // Événements pour les onglets
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', switchTab);
    });
    
    // Événements pour les dropdowns de traces (seulement static et dynamic)
    document.getElementById('staticTraceSelect').addEventListener('change', () => updateChart('static'));
    document.getElementById('dynamicTraceSelect').addEventListener('change', () => updateChart('dynamic'));
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
    
    // Catégoriser les traces selon les nouvelles règles
    currentStudentTraces = categorizeTraces(studentTraces);
    
    // Nettoyer les anciens graphiques
    Object.values(chartsInstances).forEach(chart => {
        if (chart && typeof chart.destroy === 'function') {
            chart.destroy();
        }
    });
    chartsInstances = {};
    
    // Peupler les dropdowns pour static et dynamic seulement
    populateTraceDropdown('staticTraceSelect', currentStudentTraces.static);
    populateTraceDropdown('dynamicTraceSelect', currentStudentTraces.dynamic);
    
    // Générer les tableaux pour les onglets suspicious et others
    generateTable('suspiciousTable', currentStudentTraces.suspicious);
    generateTable('othersTable', currentStudentTraces.others);
    
    // Rester sur l'onglet actuel
    switchToTab(currentTab);
    
    document.getElementById('studentDashboard').style.display = 'block';
}

function categorizeTraces(traces) {
    const categorized = {
        static: [],
        dynamic: [],
        suspicious: [],
        others: []
    };
    
    traces.forEach(trace => {
        const categories = trace.trace.category || [];
        
        if (categories.includes('Suspicious') || categories.length === 0) {
            // Suspicious ou sans catégorie -> tableau
            if (categories.includes('Suspicious')) {
                categorized.suspicious.push(trace);
            } else {
                categorized.others.push(trace);
            }
        } else if (categories.includes('Static')) {
            categorized.static.push(trace);
        } else if (categories.includes('Dynamic')) {
            categorized.dynamic.push(trace);
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
    
    // Déterminer quelle trace sélectionner
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
    
    if (tabName === 'static' || tabName === 'dynamic') {
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
    
    // Obtenir toutes les traces de ce type pour la moyenne de classe
    const categoryName = category === 'static' ? 'Static' : 'Dynamic';
    const allTraces = currentData.traces.filter(trace => {
        return trace.trace.trace_name === traceName &&
               trace.trace.category && trace.trace.category.includes(categoryName);
    });
    
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
    
    const firstValue = sortedStudentTraces[0].trace.value;
    
    if (typeof firstValue === 'number') {
        createNumericChart(sortedStudentTraces, allTraces, canvas, canvasId);
    } else {
        createTextualChart(sortedStudentTraces, canvas, canvasId);
    }
}

function createNumericChart(studentTraces, allTraces, canvas, canvasId) {
    const labels = studentTraces.map(trace => {
        const date = new Date(trace.trace.timestamp);
        return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    });
    
    const studentData = studentTraces.map(trace => trace.trace.value);
    
    const datasets = [{
        label: 'Étudiant',
        data: studentData,
        borderColor: '#007bff',
        backgroundColor: 'rgba(0, 123, 255, 0.1)',
        fill: false,
        tension: 0.4
    }];
    
    // Calculer la moyenne de classe
    const allNumericTraces = allTraces.filter(t => typeof t.trace.value === 'number');
    if (allNumericTraces.length > 0) {
        const allNumericValues = allNumericTraces.map(t => t.trace.value);
        const classAverage = allNumericValues.reduce((sum, val) => sum + val, 0) / allNumericValues.length;
        
        const classAverageData = new Array(studentData.length).fill(classAverage);
        datasets.push({
            label: `Moyenne classe (${Math.round(classAverage)})`,
            data: classAverageData,
            borderColor: '#dc3545',
            borderDash: [5, 5],
            fill: false
        });
    }
    
    const ctx = canvas.getContext('2d');
    chartsInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            animation: false,
            scales: {
                x: { title: { display: true, text: 'Temps' } },
                y: { beginAtZero: true, title: { display: true, text: 'Valeur' } }
            },
            plugins: { legend: { display: true, position: 'top' } }
        }
    });
}

function createTextualChart(studentTraces, canvas, canvasId) {
    // Points colorés pour les valeurs textuelles
    const allValues = [...new Set(studentTraces.map(t => t.trace.value))];
    const colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c'];
    const colorMap = {};
    
    allValues.forEach((value, index) => {
        colorMap[value] = colors[index % colors.length];
    });
    
    const labels = studentTraces.map(trace => {
        const date = new Date(trace.trace.timestamp);
        return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    });
    
    const datasets = [];
    allValues.forEach(value => {
        const data = studentTraces.map(trace => trace.trace.value === value ? 1 : null);
        
        datasets.push({
            label: value,
            data: data,
            backgroundColor: colorMap[value],
            borderColor: colorMap[value],
            pointRadius: 8,
            showLine: false,
            fill: false
        });
    });
    
    const ctx = canvas.getContext('2d');
    chartsInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            animation: false,
            scales: {
                x: { title: { display: true, text: 'Temps' } },
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