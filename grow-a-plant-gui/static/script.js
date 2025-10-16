// Initialize Socket.IO connection
const socket = io();

// State
let brokerRunning = false;
let simulationRunning = false;
let controllerRunning = false;

// Connect to Socket.IO
socket.on('connect', () => {
    console.log('Connected to server');
    addAlert('success', 'Connected to server');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    addAlert('warning', 'Disconnected from server');
});

// Listen for broker status updates
socket.on('broker_status', (data) => {
    brokerRunning = data.running;
    updateBrokerUI();
});

// Listen for simulation status updates
socket.on('simulation_status', (data) => {
    simulationRunning = data.running;
    updateSimulationUI();
});

// Listen for metrics updates
socket.on('metrics_update', (metrics) => {
    updateMetrics(metrics);
});

// Listen for controller status updates
socket.on('controller_status', (data) => {
    controllerRunning = data.running;
    updateControllerUI();
});

// Listen for automatic watering alerts
socket.on('auto_water_alert', (data) => {
    addAlert('danger', data.message);
    console.log('[AUTO-WATER]', data.message);
});

// Poll status periodically
function pollStatus() {
    fetch('/api/status?_=' + Date.now()) // Cache buster
        .then(response => response.json())
        .then(status => {
            brokerRunning = status.mqtt_broker_running;
            simulationRunning = status.simulation_running;
            controllerRunning = status.controller_running;
            
            updateBrokerUI();
            updateSimulationUI();
            updateControllerUI();
            
            if (status.metrics) {
                updateMetrics(status.metrics);
            }
        })
        .catch(error => console.error('Status poll error:', error));
}

// Toggle MQTT Broker
async function toggleBroker() {
    const endpoint = brokerRunning ? '/api/stop_broker' : '/api/start_broker';
    
    try {
        const response = await fetch(endpoint, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            addAlert('success', data.message);
            // Immediately poll status
            setTimeout(pollStatus, 500);
        } else {
            addAlert('danger', data.message);
        }
    } catch (error) {
        addAlert('danger', 'Error communicating with server');
    }
}

// Toggle Simulation
async function toggleSimulation() {
    const endpoint = simulationRunning ? '/api/stop_simulation' : '/api/start_simulation';
    
    try {
        const response = await fetch(endpoint, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            addAlert('success', data.message);
            // Immediately poll status
            setTimeout(pollStatus, 500);
        } else {
            addAlert('danger', data.message);
        }
    } catch (error) {
        addAlert('danger', 'Error communicating with server');
    }
}

// Update Broker UI
function updateBrokerUI() {
    const btn = document.getElementById('broker-btn');
    const statusDot = document.querySelector('#broker-status .status-dot');
    const statusText = document.querySelector('#broker-status .status-text');
    
    console.log('Broker UI update:', brokerRunning); // Debug
    
    if (brokerRunning) {
        btn.textContent = 'Stop MQTT Broker';
        btn.classList.add('active');
        statusDot.classList.add('active');
        statusText.classList.add('active');
        statusText.textContent = 'Running';
    } else {
        btn.textContent = 'Start MQTT Broker';
        btn.classList.remove('active');
        statusDot.classList.remove('active');
        statusText.classList.remove('active');
        statusText.textContent = 'Stopped';
    }
}

// Update Simulation UI
function updateSimulationUI() {
    const btn = document.getElementById('simulation-btn');
    const statusDot = document.querySelector('#simulation-status .status-dot');
    const statusText = document.querySelector('#simulation-status .status-text');
    
    if (simulationRunning) {
        btn.textContent = 'Stop Simulation';
        btn.classList.add('active');
        statusDot.classList.add('active');
        statusText.classList.add('active');
        statusText.textContent = 'Running';
    } else {
        btn.textContent = 'Start Simulation';
        btn.classList.remove('active');
        statusDot.classList.remove('active');
        statusText.classList.remove('active');
        statusText.textContent = 'Stopped';
    }
}

// Update metrics display
function updateMetrics(metrics) {
    // Update moisture - only if simulator has published data
    if (metrics.soil_moisture !== null && metrics.soil_moisture !== undefined) {
        document.getElementById('moisture-value').textContent = metrics.soil_moisture.toFixed(1) + '%';
        document.getElementById('moisture-bar').style.width = metrics.soil_moisture + '%';
    } else {
        document.getElementById('moisture-value').textContent = 'Waiting for simulator...';
        document.getElementById('moisture-bar').style.width = '0%';
    }
    
    // Update temperature - only if simulator has published data
    if (metrics.temperature !== null && metrics.temperature !== undefined) {
        document.getElementById('temperature-value').textContent = metrics.temperature.toFixed(1) + '°C';
        const tempPercent = ((metrics.temperature - 0) / 50) * 100; // Scale 0-50°C to 0-100%
        document.getElementById('temperature-bar').style.width = Math.min(100, tempPercent) + '%';
    } else {
        document.getElementById('temperature-value').textContent = 'Waiting for simulator...';
        document.getElementById('temperature-bar').style.width = '0%';
    }
    
    // Update watering hours
    document.getElementById('watering-hours-value').textContent = metrics.watering_hours.toFixed(1) + ' hours';
    const hoursPercent = (metrics.watering_hours / 24) * 100;
    document.getElementById('watering-bar').style.width = hoursPercent + '%';
    
    // Update plant health
    document.getElementById('health-value').textContent = metrics.plant_health + '%';
    document.getElementById('health-bar').style.width = metrics.plant_health + '%';
    
    // Update faucet status indicator
    updateFaucetStatus(metrics.faucet_status);
    
    // Update plant box
    updatePlantBox(metrics);
    
    // Check for alerts - only if we have valid sensor data
    if (metrics.soil_moisture !== null && metrics.temperature !== null) {
        checkAlerts(metrics);
    }
}

// Update faucet status indicator
function updateFaucetStatus(status) {
    const waterBtn = document.getElementById('water-btn');
    const faucetValue = document.getElementById('faucet-value');
    const faucetStatusText = document.getElementById('faucet-status-text');
    const faucetCard = document.getElementById('faucet-card');

    if (status === 1) {
        // Faucet is ON - show stop button
        waterBtn.classList.add('faucet-on');
        waterBtn.textContent = '🛑 Stop Faucet';
        waterBtn.disabled = false;  // Enable so user can stop it

        // Update faucet status card
        faucetValue.textContent = 'ON';
        faucetValue.style.color = '#4CAF50';
        faucetValue.style.fontWeight = 'bold';
        faucetStatusText.textContent = '💧 Water flowing...';
        faucetCard.style.borderColor = '#4CAF50';
        faucetCard.style.backgroundColor = '#e8f5e9';
    } else {
        // Faucet is OFF - show water button
        waterBtn.classList.remove('faucet-on');
        waterBtn.textContent = '💧 Water Plant';
        waterBtn.disabled = false;

        // Update faucet status card
        faucetValue.textContent = 'OFF';
        faucetValue.style.color = '#999';
        faucetValue.style.fontWeight = 'normal';
        faucetStatusText.textContent = 'Not watering';
        faucetCard.style.borderColor = '#ddd';
        faucetCard.style.backgroundColor = '#fff';
    }
}

// Update plant box appearance
function updatePlantBox(metrics) {
    const plantBox = document.getElementById('plant-box');
    const plantStatus = document.getElementById('plant-status-text');
    const plantEmoji = document.querySelector('.plant-emoji');
    
    // Remove existing classes
    plantBox.classList.remove('healthy', 'warning');
    
    if (metrics.plant_health >= 70) {
        plantBox.classList.add('healthy');
        plantStatus.textContent = '🌟 Plant is healthy and thriving!';
        plantEmoji.textContent = '🌿';
    } else if (metrics.plant_health >= 40) {
        plantStatus.textContent = '⚠️ Plant needs attention';
        plantEmoji.textContent = '🌱';
    } else {
        plantBox.classList.add('warning');
        plantStatus.textContent = '⚠️ Critical: Immediate action required!';
        plantEmoji.textContent = '🥀';
    }
    
    // Show watering status
    if (metrics.currently_watering === 1) {
        plantStatus.textContent += ' 💧 Needs watering!';
    }
}

// Check for alerts
function checkAlerts(metrics) {
    // Low moisture alert
    if (metrics.soil_moisture < 30) {
        addAlert('danger', '💧 Low soil moisture detected! Plant needs watering urgently.');
    }
    
    // High temperature alert
    if (metrics.temperature > 30) {
        addAlert('warning', '🌡️ High temperature detected! Monitor plant closely.');
    }
    
    // Low health alert
    if (metrics.plant_health < 40) {
        addAlert('danger', '⚠️ Plant health is critical! Take immediate action.');
    }
}

// Add alert to alerts container
let alertCounter = 0;
function addAlert(type, message) {
    const alertsContainer = document.getElementById('alerts-container');
    const alertId = 'alert-' + alertCounter++;
    
    // Check if similar alert already exists
    const existingAlerts = alertsContainer.querySelectorAll('.alert');
    for (let alert of existingAlerts) {
        if (alert.textContent.includes(message.split('.')[0])) {
            return; // Don't add duplicate alerts
        }
    }
    
    // Create new alert
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.id = alertId;
    alert.innerHTML = `<strong>${getAlertIcon(type)} ${message}</strong>`;
    
    // Add to container
    alertsContainer.insertBefore(alert, alertsContainer.firstChild);
    
    // Remove after 10 seconds
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            alertElement.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => alertElement.remove(), 300);
        }
    }, 10000);
    
    // Keep only last 5 alerts
    while (alertsContainer.children.length > 5) {
        alertsContainer.removeChild(alertsContainer.lastChild);
    }
}

function getAlertIcon(type) {
    switch (type) {
        case 'success': return '✅';
        case 'warning': return '⚠️';
        case 'danger': return '🚨';
        default: return 'ℹ️';
    }
}

// Toggle Plant Controller
async function toggleController() {
    const endpoint = controllerRunning ? '/api/stop_controller' : '/api/start_controller';
    
    try {
        const response = await fetch(endpoint, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            addAlert('success', data.message);
            // Immediately poll status
            setTimeout(pollStatus, 500);
        } else {
            addAlert('danger', data.message);
        }
    } catch (error) {
        addAlert('danger', 'Error communicating with server');
    }
}

// Water the Plant / Stop Faucet (toggle)
async function waterPlant() {
    try {
        // Check current faucet status from metrics
        const statusResponse = await fetch('/api/status');
        const status = await statusResponse.json();
        const faucetOn = status.metrics.faucet_status === 1;
        
        // Toggle: if faucet is ON, turn it OFF; if OFF, turn it ON
        const endpoint = faucetOn ? '/api/stop_faucet' : '/api/water_plant';
        
        const response = await fetch(endpoint, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            addAlert('success', data.message);
            // Immediately poll status
            setTimeout(pollStatus, 500);
        } else {
            addAlert('warning', data.message);
        }
    } catch (error) {
        addAlert('danger', 'Error controlling faucet');
    }
}

// Update Controller UI
function updateControllerUI() {
    const btn = document.getElementById('controller-btn');
    const statusDot = document.querySelector('#controller-status .status-dot');
    const statusText = document.querySelector('#controller-status .status-text');
    
    if (controllerRunning) {
        btn.textContent = 'Stop Controller';
        btn.classList.add('active');
        statusDot.classList.add('active');
        statusText.classList.add('active');
        statusText.textContent = 'Running';
    } else {
        btn.textContent = 'Start Controller';
        btn.classList.remove('active');
        statusDot.classList.remove('active');
        statusText.classList.remove('active');
        statusText.textContent = 'Stopped';
    }
}

// Load configuration
async function loadConfig() {
    try {
        const response = await fetch('/api/get_config');
        const data = await response.json();
        
        if (data.success) {
            const thresholds = data.config.message_flows[0].thresholds;
            document.getElementById('moisture-low').value = thresholds.moisture_low;
            document.getElementById('moisture-optimal').value = thresholds.moisture_optimal;
            document.getElementById('temp-low').value = thresholds.temp_low;
            document.getElementById('temp-high').value = thresholds.temp_high;
            addAlert('success', '✅ Configuration loaded');
        } else {
            addAlert('danger', data.message);
        }
    } catch (error) {
        addAlert('danger', 'Error loading configuration');
    }
}

// Save configuration
async function saveConfig() {
    try {
        const thresholds = {
            moisture_low: parseInt(document.getElementById('moisture-low').value),
            moisture_optimal: parseInt(document.getElementById('moisture-optimal').value),
            temp_low: parseInt(document.getElementById('temp-low').value),
            temp_high: parseInt(document.getElementById('temp-high').value)
        };
        
        const response = await fetch('/api/update_config', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({thresholds})
        });
        
        const data = await response.json();
        
        if (data.success) {
            addAlert('success', data.message);
        } else {
            addAlert('danger', data.message);
        }
    } catch (error) {
        addAlert('danger', 'Error saving configuration');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Dashboard loaded - v' + Date.now()); // Version stamp
    
    // Load initial status from server with cache buster
    try {
        const response = await fetch('/api/status?_=' + Date.now());
        const status = await response.json();
        
        console.log('Initial status:', status); // Debug
        
        brokerRunning = status.mqtt_broker_running;
        simulationRunning = status.simulation_running;
        controllerRunning = status.controller_running;
        
        updateBrokerUI();
        updateSimulationUI();
        updateControllerUI();
        
        // Update metrics if available
        if (status.metrics) {
            updateMetrics(status.metrics);
        }
        
        // Load current configuration
        loadConfig();
        
        // Start polling status every 3 seconds
        setInterval(pollStatus, 3000);
        console.log('Status polling started');
    } catch (error) {
        console.error('Error loading initial status:', error);
    }
});
