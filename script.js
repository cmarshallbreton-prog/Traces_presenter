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
    
    // Sauvegarder les traces de l'étudiant
    currentStudentTraces = categorizeTraces(studentTraces);
    
    // Nettoyer les anciens graphiques
    Object.values(chartsInstances).forEach(chart => {
        if (chart && typeof chart.destroy === 'function') {
            chart.destroy();
        }
    });
    chartsInstances = {};
    
    // Peupler les dropdowns pour les onglets avec graphiques
    populateTraceDropdown('staticTraceSelect', currentStudentTraces.static);
    populateTraceDropdown('dynamicTraceSelect', currentStudentTraces.dynamic);
    
    // Générer les tableaux pour les onglets suspicious et others
    generateSuspiciousTable(currentStudentTraces.suspicious);
    generateOthersTable(currentStudentTraces.others);
    
    // Rester sur l'onglet actuel ou aller sur statique par défaut
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
        
        if (categories.includes('Static')) {
            categorized.static.push(trace);
        } else if (categories.includes('Dynamic')) {
            categorized.dynamic.push(trace);
        } else if (categories.includes('Suspicious')) {
            categorized.suspicious.push(trace);
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
    
    // Vider la dropdown
    select.innerHTML = '';
    
    // Déterminer quelle trace sélectionner
    const category = selectId.replace('TraceSelect', '');
    let selectedTrace = null;
    
    // Si on a une trace mémorisée pour cette catégorie et qu'elle existe encore
    if (selectedTraces[category] && traceNames.includes(selectedTraces[category])) {
        selectedTrace = selectedTraces[category];
    } else {
        // Sinon, prendre la première trace disponible
        selectedTrace = traceNames[0];
        selectedTraces[category] = selectedTrace;
    }
    
    // Ajouter toutes les traces à la dropdown
    traceNames.forEach(traceName => {
        const option = document.createElement('option');
        option.value = traceName;
        option.textContent = traceName;
        if (traceName === selectedTrace) {
            option.selected = true;
        }
        select.appendChild(option);
    });
    
    // Déclencher automatiquement l'affichage du graphique si on est sur l'onglet actuel
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
    
    // Mettre à jour les boutons d'onglets
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tabName) {
            btn.classList.add('active');
        }
    });
    
    // Mettre à jour le contenu des onglets
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    const targetTab = document.getElementById(tabName + 'Tab');
    if (targetTab) {
        targetTab.classList.add('active');
    }
    
    // Pour les onglets avec graphiques, déclencher automatiquement l'affichage
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
        // Nettoyer le graphique
        if (chartsInstances[canvasId]) {
            chartsInstances[canvasId].destroy();
            delete chartsInstances[canvasId];
        }
        return;
    }
    
    // Mémoriser la trace sélectionnée
    selectedTraces[category] = selectedTrace;
    
    // Filtrer les traces pour la trace sélectionnée
    const categoryTraces = currentStudentTraces[category];
    const selectedTraces_data = categoryTraces.filter(trace => trace.trace.trace_name === selectedTrace);
    
    // Mettre à jour le titre
    chartTitle.textContent = `Évolution : ${selectedTrace}`;
    
    // Créer le graphique d'évolution avec moyenne de classe
    createEvolutionChart(selectedTraces_data, canvasId, category, selectedTrace);
}

function createEvolutionChart(studentTraces, canvasId, category, traceName) {
    // Détruire le graphique existant
    if (chartsInstances[canvasId]) {
        chartsInstances[canvasId].destroy();
        delete chartsInstances[canvasId];
    }
    
    const canvas = document.getElementById(canvasId);
    if (!canvas) {
        console.error(`Canvas ${canvasId} not found`);
        return;
    }
    
    console.log(`Creating chart for ${traceName} in category ${category} with ${studentTraces.length} traces`); // Debug
    
    // Mapping des catégories avec la bonne casse
    const categoryMap = {
        'static': 'Static',
        'dynamic': 'Dynamic',
        'suspicious': 'Suspicious',
        'others': 'others'
    };
    
    const actualCategory = categoryMap[category];
    console.log(`Mapped category ${category} to ${actualCategory}`); // Debug
    
    // Obtenir toutes les traces de ce type pour calculer la moyenne de classe
    console.log('Filtering all traces for class average...'); // Debug
    
    let allTraces;
    if (category === 'others') {
        // Pour "others", on prend les traces sans catégorie spécifique
        allTraces = currentData.traces.filter(trace => {
            const categories = trace.trace.category || [];
            const isOthers = categories.length === 0 || 
                           (!categories.includes('Static') && 
                            !categories.includes('Dynamic') && 
                            !categories.includes('Suspicious'));
            return trace.trace.trace_name === traceName && isOthers;
        });
    } else {
        // Pour les autres catégories, filtrer par nom de trace ET par catégorie (avec la bonne casse)
        allTraces = currentData.traces.filter(trace => {
            if (trace.trace.trace_name !== traceName) return false;
            
            const categories = trace.trace.category || [];
            const hasCategory = categories.includes(actualCategory);
            
            console.log(`Trace: ${trace.trace.trace_name}, Categories: [${categories.join(', ')}], Has ${actualCategory}: ${hasCategory}`); // Debug
            return hasCategory;
        });
    }
    
    console.log(`Found ${allTraces.length} traces in total for ${traceName} in category ${actualCategory}`); // Debug
    
    // Debug: afficher quelques exemples de traces trouvées
    if (allTraces.length > 0) {
        console.log('Sample traces found:');
        allTraces.slice(0, 3).forEach(trace => {
            console.log(`- Student: ${trace.student_name}, Value: ${trace.trace.value}, Categories: [${(trace.trace.category || []).join(', ')}]`);
        });
    }
    
    // Trier les traces de l'étudiant par timestamp
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
    
    // Préparer les données selon le type de valeur
    const datasets = [];
    
    // Vérifier le type de données
    const firstValue = sortedStudentTraces[0].trace.value;
    console.log(`First value type: ${typeof firstValue}, value: ${firstValue}`); // Debug
    
    // Créer les labels temporels simples
    const labels = sortedStudentTraces.map((trace, index) => {
        const date = new Date(trace.trace.timestamp);
        return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    });
    
    if (typeof firstValue === 'number') {
        // Données numériques
        const studentData = sortedStudentTraces.map(trace => trace.trace.value);
        
        // Calculer la moyenne de classe
        const allNumericTraces = allTraces.filter(t => typeof t.trace.value === 'number');
        console.log(`Found ${allNumericTraces.length} numeric traces for class average`); // Debug
        
        if (allNumericTraces.length > 0) {
            const allNumericValues = allNumericTraces.map(t => t.trace.value);
            console.log(`Numeric values: [${allNumericValues.slice(0, 5).join(', ')}${allNumericValues.length > 5 ? '...' : ''}]`); // Debug
            
            const classAverage = allNumericValues.reduce((sum, val) => sum + val, 0) / allNumericValues.length;
            console.log(`Calculated class average: ${classAverage}`); // Debug
            
            // Dataset pour l'étudiant
            datasets.push({
                label: 'Étudiant',
                data: studentData,
                borderColor: '#007bff',
                backgroundColor: 'rgba(0, 123, 255, 0.1)',
                fill: false,
                tension: 0.4
            });
            
            // Dataset pour la moyenne de classe (ligne horizontale)
            const classAverageData = new Array(studentData.length).fill(classAverage);
            datasets.push({
                label: `Moyenne classe (${Math.round(classAverage)})`,
                data: classAverageData,
                borderColor: '#dc3545',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                borderDash: [5, 5],
                fill: false
            });
        } else {
            console.log('No numeric traces found for class average'); // Debug
            // Seulement l'étudiant
            datasets.push({
                label: 'Étudiant',
                data: studentData,
                borderColor: '#007bff',
                backgroundColor: 'rgba(0, 123, 255, 0.1)',
                fill: false,
                tension: 0.4
            });
        }
        
    } else if (firstValue === 'success' || firstValue === 'failure') {
        // Données de tests (success/failure)
        const studentData = sortedStudentTraces.map(trace => 
            trace.trace.value === 'success' ? 1 : 0
        );
        
        // Calculer le taux de réussite de la classe
        const allTestTraces = allTraces.filter(t => 
            t.trace.value === 'success' || t.trace.value === 'failure'
        );
        console.log(`Found ${allTestTraces.length} test traces for success rate`); // Debug
        
        if (allTestTraces.length > 0) {
            const successCount = allTestTraces.filter(t => t.trace.value === 'success').length;
            const successRate = successCount / allTestTraces.length;
            console.log(`Success rate: ${successCount}/${allTestTraces.length} = ${successRate}`); // Debug
            
            // Dataset pour l'étudiant
            datasets.push({
                label: 'Étudiant',
                data: studentData,
                borderColor: '#28a745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                fill: false,
                stepped: true
            });
            
            // Dataset pour la moyenne de classe
            const classRateData = new Array(studentData.length).fill(successRate);
            datasets.push({
                label: `Taux de réussite classe (${Math.round(successRate * 100)}%)`,
                data: classRateData,
                borderColor: '#dc3545',
                backgroundColor: 'rgba(220, 53, 69, 0.1)',
                borderDash: [5, 5],
                fill: false
            });
        } else {
            console.log('No test traces found for class average'); // Debug
            // Seulement l'étudiant
            datasets.push({
                label: 'Étudiant',
                data: studentData,
                borderColor: '#28a745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                fill: false,
                stepped: true
            });
        }
        
    } else {
        // Autres types de données (oui/non, etc.)
        console.log('Processing other data types'); // Debug
        const uniqueValues = [...new Set(allTraces.map(t => t.trace.value).filter(v => v !== undefined))];
        console.log(`Unique values found: [${uniqueValues.join(', ')}]`); // Debug
        
        const valueMap = {};
        uniqueValues.forEach((value, index) => {
            valueMap[value] = index;
        });
        
        const studentData = sortedStudentTraces.map(trace => 
            valueMap[trace.trace.value] !== undefined ? valueMap[trace.trace.value] : 0
        );
        
        datasets.push({
            label: 'Étudiant',
            data: studentData,
            borderColor: '#6f42c1',
            backgroundColor: 'rgba(111, 66, 193, 0.1)',
            fill: false,
            stepped: true
        });
    }
    
    console.log('Creating chart with datasets:', datasets.length, 'datasets'); // Debug
    
    // Créer le graphique
    const ctx = canvas.getContext('2d');
    chartsInstances[canvasId] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            animation: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Temps'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: typeof firstValue === 'number' ? 'Valeur' : 
                              (firstValue === 'success' || firstValue === 'failure') ? 'Résultat' : 'Valeur'
                    },
                    ticks: typeof firstValue === 'number' ? {} : 
                          (firstValue === 'success' || firstValue === 'failure') ? {
                        callback: function(value) {
                            return value === 1 ? 'Succès' : 'Échec';
                        }
                    } : {}
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            }
        }
    });
    
    console.log('Chart created successfully'); // Debug
}

function generateSuspiciousTable(suspiciousTraces) {
    const tableContainer = document.getElementById('suspiciousTable');
    
    if (!tableContainer) {
        console.error('Element suspiciousTable not found');
        return;
    }
    
    if (suspiciousTraces.length === 0) {
        tableContainer.innerHTML = '<div class="no-data">Aucune trace suspecte pour cet étudiant</div>';
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
    
    // Trier par timestamp
    const sortedTraces = suspiciousTraces.sort((a, b) => 
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

function generateOthersTable(otherTraces) {
    const tableContainer = document.getElementById('othersTable');
    
    if (!tableContainer) {
        console.error('Element othersTable not found');
        return;
    }
    
    if (otherTraces.length === 0) {
        tableContainer.innerHTML = '<div class="no-data">Aucune autre trace pour cet étudiant</div>';
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
    
    // Trier par timestamp
    const sortedTraces = otherTraces.sort((a, b) => 
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