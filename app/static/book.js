function updateUI() {
    const elements = {
        categorySelect: document.getElementById("category"),
        dateTimeDiv: document.getElementById("date_time_div"),
        recurrenceSection: document.getElementById("recurrence_section"),
        commuteTimesSection: document.getElementById("commute_times_section"),
        dateTimeInput: document.getElementById("date_time"),
    };

    if (!elements.categorySelect || !elements.dateTimeDiv || !elements.recurrenceSection || !elements.commuteTimesSection || !elements.dateTimeInput) {
        console.error("One or more elements are missing in the DOM!");
        return; 
    }

    const isOneTime = elements.categorySelect.value === "one-time";
    elements.dateTimeDiv.style.display = isOneTime ? "block" : "none";
    elements.recurrenceSection.style.display = isOneTime ? "none" : "block";
    elements.commuteTimesSection.style.display = isOneTime ? "none" : "block";
    elements.dateTimeInput.required = isOneTime;
}

function fetchAvailableSeats(selectedDates) {
    let availableSeatsElement = document.getElementById("availableSeats");
    let rideIdElement = document.getElementById("ride_id");
    let rideId = rideIdElement ? rideIdElement.value : null;

    if (!rideId) {
        console.error(" Ride ID not found!");
        return;
    }

    if (!selectedDates || selectedDates.length === 0) {
        console.warn(" No dates selected for fetching available seats.");
        availableSeatsElement.textContent = "N/A";
        return;
    }

    let formattedDates = selectedDates.map(date => new Date(date).toISOString().split('T')[0]);
    console.log("Fetching available seats for:", formattedDates);

    // Use GET instead of POST
    fetch(`/api/get_available_seats/${rideId}?selected_dates=${formattedDates.join(",")}`)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log("API Response:", data);
        if (!data.available_seats || Object.keys(data.available_seats).length === 0) {
            console.warn(" No available seats data received from API.");
            availableSeatsElement.textContent = "0";
            return;
        }

        let minSeats = Math.min(...Object.values(data.available_seats));
        availableSeatsElement.textContent = minSeats || 0;
    })
    .catch(error => {
        console.error("Error fetching available seats:", error);
        availableSeatsElement.textContent = "Error";
    });
}


// Fetch Available Dates Function
function fetchAvailableDates() {
    let selectedDatesInput = document.querySelector("#selected_dates");
    let rideIdElement = document.getElementById("ride_id");
    let rideId = rideIdElement ? rideIdElement.value : null;

    if (!selectedDatesInput || !rideId) {
        console.error("Missing selectedDatesInput or rideId");
        return;
    }

    fetch(`/api/get_available_dates/${rideId}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            console.log(" API Response (Available Dates):", data);
            if (!data.available_dates || data.available_dates.length === 0) {
                console.warn("No available dates returned from API.");
                return;
            }

            flatpickr(selectedDatesInput, {
                mode: "multiple",
                dateFormat: "Y-m-d",
                disableMobile: true,
                enable: data.available_dates,  // Only allow valid dates
                clickOpens: true,  // Ensures calendar only opens on click
                allowInput: false,  // Prevents manual typing
                onChange: function (selectedDates, dateStr, instance) {
                    console.log("Selected Dates:", selectedDates);
                    if (selectedDates.length > 0) {
                        fetchAvailableSeats(selectedDates);
                    }
                }
            });
        })
        .catch(error => console.error("Error fetching available dates:", error));
}

// Event Listener for UI & Initialization
document.addEventListener("DOMContentLoaded", function () {
    updateUI(); // Initialize UI

    let categorySelect = document.getElementById("category");
    if (categorySelect) {
        categorySelect.addEventListener("change", updateUI);
    }

    fetchAvailableDates(); // Fetch available dates on page load

    // Initialize Flatpickr for Date & Time Selection
    if (document.querySelector("#date_time")) {
        flatpickr("#date_time", { enableTime: true, dateFormat: "Y-m-d H:i", disableMobile: true });
    }
    if (document.querySelector("#recurrence_dates")) {
        flatpickr("#recurrence_dates", { mode: "multiple", dateFormat: "Y-m-d", disableMobile: true });
    }
    if (document.querySelector("#commute_times")) {
        flatpickr("#commute_times", { enableTime: true, noCalendar: true, mode: "multiple", dateFormat: "H:i", disableMobile: true });
    }

    // Calculate Total Price When Selecting Seats
    let seatsInput = document.getElementById("seats");
    let totalPriceInput = document.getElementById("total_price");
    let pricePerSeatElement = document.getElementById("price_per_seat");
    let availableSeatsElement = document.getElementById("availableSeats");

    if (seatsInput && totalPriceInput && pricePerSeatElement && availableSeatsElement) {
        let pricePerSeat = parseFloat(pricePerSeatElement.dataset.price);
        let availableSeats = parseInt(availableSeatsElement.textContent); 

        if (isNaN(pricePerSeat)) pricePerSeat = 0;
        if (isNaN(availableSeats)) availableSeats = 0;

        seatsInput.addEventListener("input", function () {
            let selectedSeats = parseInt(this.value);
            let availableSeats = parseInt(availableSeatsElement.textContent);
            let pricePerSeat = parseFloat(pricePerSeatElement.dataset.price);
        
            if (isNaN(selectedSeats) || selectedSeats <= 0) {
                totalPriceInput.value = "0.00"; 
                return;
            }
        
            if (selectedSeats > availableSeats) {
                alert("Not enough available seats!");
                this.value = availableSeats;
                selectedSeats = availableSeats;
            }
        
            totalPriceInput.value = (selectedSeats * pricePerSeat).toFixed(2);
        });
        
    }

    // Toggle Bookings Section
    let toggleBookingsBtn = document.getElementById("toggleBookings");
    let bookingsContainer = document.getElementById("bookingsContainer");

    if (toggleBookingsBtn && bookingsContainer) {
        toggleBookingsBtn.addEventListener("click", function () {
            bookingsContainer.style.display = (bookingsContainer.style.display === "none") ? "block" : "none";
        });
    }

    // Handle Proceed to Payment Button Click
    let proceedToPaymentBtn = document.getElementById("proceedToPayment");
    if (proceedToPaymentBtn) {
        proceedToPaymentBtn.addEventListener("click", function () {
            console.log(" Proceeding to Payment...");

            const rideId = document.getElementById("ride_id").value;
            const seats = document.getElementById("seats").value;
            const totalPrice = document.getElementById("total_price").value;

            if (!rideId || !seats || seats <= 0 || !totalPrice || totalPrice <= 0) {
                alert(" Please select valid seats before proceeding!");
                return;
            }

            // Redirect to the payment page
            const paymentUrl = `/payment/${rideId}/${seats}/${totalPrice}`;
            console.log(` Redirecting to: ${paymentUrl}`);
            window.location.href = paymentUrl;
        });
    }

});
