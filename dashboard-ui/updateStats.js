/* UPDATE THESE VALUES TO MATCH YOUR SETUP */

const STATS_API_URL = "http://mysql-kafka.westus3.cloudapp.azure.com/processing/stats"
const EVENTS_URL = {
    print_success: "http://mysql-kafka.westus3.cloudapp.azure.com/audit_log/print_success",
    failed_print: "http://mysql-kafka.westus3.cloudapp.azure.com/audit_log/failed_print",
}
const EVENT_LOG_URL = "http://mysql-kafka.westus3.cloudapp.azure.com:8120/event_stats"
const ANOMALY = "http://mysql-kafka.westus3.cloudapp.azure.com/anomaly_detector/anomalies"

// This function fetches and updates the general statistics
const getStats = (statsUrl) => {
    fetch(statsUrl)
        .then(res => res.json())
        .then((result) => {
            console.log("Received stats", result)
            updateStatsHTML(result);
        }).catch((error) => {
            updateStatsHTML(error.message, error = true)
        })
}

const getAnomaly = (eventType) => {
    fetch(`${ANOMALY}?anomaly_type=${eventType}`)
        .then(res => {
            if (!res.ok) {
                throw new Error(`Error: status code ${res.status}`)
            }
            return res.json()
        })
        .then((result) => {
            console.log("Received event", result)
            updateAnomalyHTML({result}, eventType)
        }).catch((error) => {
            updateAnomalyHTML({error: error.message}, eventType, error = true)
        })
}

// This function fetches a single event from the audit service
const getEvent = (eventType) => {
    // const eventIndex = 0
    const eventIndex = Math.floor(Math.random() * 100)

    fetch(`${EVENTS_URL[eventType]}?index=${eventIndex}`)
        .then(res => {
            if (!res.ok) {
                throw new Error(`Error: status code ${res.status}`)
            }
            return res.json()
        })
        .then((result) => {
            console.log("Received event", result)
            updateEventHTML({...result, index: eventIndex}, eventType)
        }).catch((error) => {
            updateEventHTML({error: error.message, index: eventIndex}, eventType, error = true)
        })
}

// This function updates a single "event box"
const updateEventHTML = (data, eventType, error = false) => {
    const { index, ...values } = data
    const elem = document.getElementById(`event-${eventType}`)
    elem.innerHTML = `<h5>Event ${index}</h5>`
    
    // for error messages
    if (error === true) {
        const errorMsg = document.createElement("code")
        errorMsg.innerHTML = values.error
        elem.appendChild(errorMsg)
        return
    }

    // loops through the object and displays it in the DOM
    Object.entries(values).map(
        ([key, value]) => {
            const labelElm = document.createElement("span")
            const valueElm = document.createElement("span")
            if (typeof value === 'object') {
                valueElm.innerText = Object.entries(value).map(
                    ([key, value]) => {
                        const labelElm = document.createElement("span")
                        const valueElm = document.createElement("span")
                        labelElm.innerText = key
                        valueElm.innerText = value
                        const pElm = document.createElement("p")
                        pElm.style.display = "flex"
                        pElm.style.flexDirection = "column"
                        pElm.appendChild(labelElm)
                        pElm.appendChild(valueElm)
                        elem.appendChild(pElm)
                    }
                )
            } else {
                labelElm.innerText = key
                valueElm.innerText = value
            }
            const pElm = document.createElement("p")
            pElm.style.display = "flex"
            pElm.style.flexDirection = "column"
            pElm.appendChild(labelElm)
            pElm.appendChild(valueElm)
            elem.appendChild(pElm)
        }
    )

}

const updateAnomalyHTML = (data, eventType, error = false) => {
    const { index, ...values } = data
    const elem = document.getElementById(`event-${eventType}`)
    elem.innerHTML = `<h5>Anomaly ${eventType}</h5>`
    // for error messages
    if (error === true) {
        const errorMsg = document.createElement("code")
        errorMsg.innerHTML = values.error
        elem.appendChild(errorMsg)
        return
    }
    Object.entries(values).map(
        ([key, value]) => {
            const labelElm = document.createElement("span")
            const valueElm = document.createElement("span")
            if (typeof value === 'object') {
                valueElm.innerText = Object.entries(value).map(
                    ([key, value]) => {
                        const labelElm = document.createElement("span")
                        const valueElm = document.createElement("span")
                        labelElm.innerText = key
                        valueElm.innerText = value
                        const pElm = document.createElement("p")
                        pElm.style.display = "flex"
                        pElm.style.flexDirection = "column"
                        pElm.appendChild(labelElm)
                        pElm.appendChild(valueElm)
                        elem.appendChild(pElm)
                    }
                )
            } else {
                labelElm.innerText = key
                valueElm.innerText = value
            }
            const pElm = document.createElement("p")
            pElm.style.display = "flex"
            pElm.style.flexDirection = "column"
            pElm.appendChild(labelElm)
            pElm.appendChild(valueElm)
            elem.appendChild(pElm)
        }
    )
}

// This function updates the main statistics div
const updateStatsHTML = (data, error = false) => {
    const elem = document.getElementById("stats")
    if (error === true) {
        elem.innerHTML = `<code>${data}</code>`
        return
    }
    elem.innerHTML = ""
    Object.entries(data).map(([key, value]) => {
        const pElm = document.createElement("p")
        pElm.innerHTML = `<strong>${key}:</strong> ${value}`
        elem.appendChild(pElm)
    })
}

// get event logs
const getEventLog = (EVENT_LOG_URL) => {
    fetch(EVENT_LOG_URL)
        .then(res => res.json())
        .then((result) => {
            console.log("Received event logs", result)
            updateEventLog(result);
        }).catch((error) => {
            updateEventLog(error.message, error = true)
        })
}

// Update the event logs
const updateEventLog = (data, error = false) => {
    const elem = document.getElementById("event_log")
    if (error === true) {
        elem.innerHTML = `<code>${data}</code>`
        return
    }
    elem.innerHTML = ""
    Object.entries(data).map(([key, value]) => {
        const pElm = document.createElement("p")
        pElm.innerHTML = `<strong>${key}:</strong> ${value}`
        elem.appendChild(pElm)
    })
}

const setup = () => {
    const interval = setInterval(() => {
        getStats(STATS_API_URL)
        getEventLog(EVENT_LOG_URL)
        getEvent("print_success")
        getEvent("failed_print")
        getAnomaly("TooHigh")
        getAnomaly("TooLow")
    }, 5000); // Update every 5 seconds

    // initial call
    getStats(STATS_API_URL)
    getEventLog(EVENT_LOG_URL)
    getEvent("print_success")
    getEvent("failed_print")
    getAnomaly("TooHigh")
    getAnomaly("TooLow")
    // clearInterval(interval);
}

document.addEventListener('DOMContentLoaded', setup)