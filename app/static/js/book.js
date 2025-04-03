// Fetch available seats based on selected dates
function fetchAvailableSeats(selectedDates) {
    const availableSeatsElement = document.getElementById("availableSeats");
    const rideIdElement = document.getElementById("ride_id");

    if (!availableSeatsElement || !rideIdElement) {
        console.error("Missing elements in fetchAvailableSeats()");
        return;
    }
        
    const rideId = rideIdElement.value;
    if (!rideId || selectedDates.length === 0) {
        availableSeatsElement.textContent = "N/A";
        return;
    }

    const formattedDates = selectedDates.map(date => new Date(date).toISOString().split('T')[0]);

    fetch(`/api/get_available_seats/${rideId}?selected_dates=${formattedDates.join(",")}`)
        .then(response => response.json())
        .then(data => {
            const availableSeats = data.available_seats || {};
            const minSeats = Math.min(...Object.values(availableSeats)) || 0;
            availableSeatsElement.textContent = minSeats;
        })
        .catch(() => {
            availableSeatsElement.textContent = "Error";
        });
}

// Fetch available dates for booking
function fetchAvailableDates() {
    const selectedDatesInput = document.querySelector("#selected_dates");
    const rideIdElement = document.getElementById("ride_id");

    if (!selectedDatesInput || !rideIdElement) return;

    fetch(`/api/get_available_dates/${rideIdElement.value}`)
        .then(response => response.json())
        .then(data => {
            if (!data.available_dates) return;
            console.log("available dates are:", data.available_dates)
            flatpickr(selectedDatesInput, {
                mode: "multiple",
                dateFormat: "Y-m-d",
                disableMobile: true,
                enable: data.available_dates,
                onChange: function (selectedDateObjs) {
                    const formattedDates = selectedDateObjs.map(date =>
                        date.toLocaleDateString('en-CA')
                    );
                    fetchAvailableSeats(formattedDates);
                }
            });
        });
}

// Get selected dates from Flatpickr input
function getSelectedDates() {
    const selectedDatesInput = document.querySelector("#selected_dates");
    if (!selectedDatesInput || !selectedDatesInput._flatpickr) return [];
    return selectedDatesInput._flatpickr.selectedDates.map(date => date.toLocaleDateString('en-CA'));
}

// Handle form submission for booking
function handleBookingSubmit(event) {
    console.log("handleBookingSubmit triggered!");

    if (event.target.id !== "bookingForm") {
        console.warn("Form ID does not match 'bookingForm'. Event ignored.");
        return;
    }

    event.preventDefault();
    console.log("Form submission prevented. Proceeding...");

    const selectedDates = getSelectedDates();

    if (selectedDates.length === 0) {
        alert("Please select at least one date before proceeding.");
        console.error("No dates selected! Blocking submission.");
        return;
    }

    const rideId = document.getElementById("ride_id")?.value;
    const seats = document.getElementById("seats")?.value;
    const totalPrice = document.getElementById("total_price")?.value;
    const confirmationEmail = document.getElementById("email")?.value;

    if (!rideId || !seats || !totalPrice || !confirmationEmail) {
        console.error("Missing required booking details! Blocking submission.");
        alert("Please complete all required fields.");
        return;
    }

    // FIX: Redirect using Flask’s expected URL structure
    let paymentUrl = `/payment/${rideId}/${seats}/${totalPrice}?email=${encodeURIComponent(confirmationEmail)}`;

    // Ensure selected dates are still passed via query parameters
    selectedDates.forEach(date => paymentUrl += `&selected_dates=${date}`);

    console.log("Redirecting to:", paymentUrl);
    window.location.href = paymentUrl;
}

// Initialize Flatpickr for date and time selection
function initializeFlatpickr() {
    if (document.querySelector("#date_time")) {
        flatpickr("#date_time", { enableTime: true, dateFormat: "Y-m-d H:i", disableMobile: false });
    }
    if (document.querySelector("#selected_dates")) {
        fetchAvailableDates();
    }
}

// Calculate total price based on selected seats
function setupSeatPriceCalculation() {
    const seatsInput = document.getElementById("seats");
    const totalPriceInput = document.getElementById("total_price");
    const pricePerSeatElement = document.getElementById("price_per_seat");
    const availableSeatsElement = document.getElementById("availableSeats");
    const selectedDatesInput = document.querySelector("#selected_dates");

    if (!seatsInput || !totalPriceInput || !pricePerSeatElement || !availableSeatsElement) return;

    const pricePerSeat = parseFloat(pricePerSeatElement.dataset.price) || 0;

    function calculateTotalPrice() {
        let selectedSeats = parseInt(seatsInput.value) || 0;
        let availableSeats = parseInt(availableSeatsElement.textContent) || 0;
        let selectedDates = 1; // Default to 1 for one-time rides

        if (selectedDatesInput && selectedDatesInput._flatpickr) {
            selectedDates = selectedDatesInput._flatpickr.selectedDates.length || 1; // Use selected dates if available
        }

        if (selectedSeats > availableSeats) {
            alert("Not enough available seats!");
            seatsInput.value = availableSeats;
            selectedSeats = availableSeats;
        }

        // Multiply by the number of selected dates
        let totalPrice = selectedSeats * selectedDates * pricePerSeat;
        totalPriceInput.value = totalPrice.toFixed(2);
    }

    seatsInput.addEventListener("input", calculateTotalPrice);
    selectedDatesInput.addEventListener("change", calculateTotalPrice);
}

// Toggle bookings section
function setupToggleBookings() {
    const toggleBookingsBtn = document.getElementById("toggleBookings");
    const bookingsContainer = document.getElementById("bookingsContainer");

    if (toggleBookingsBtn && bookingsContainer) {
        toggleBookingsBtn.addEventListener("click", () => {
            bookingsContainer.style.display = bookingsContainer.style.display === "none" ? "block" : "none";
        });
    }
}

// Initialize all event listeners
document.addEventListener("DOMContentLoaded", () => {
    initializeFlatpickr();
    setupSeatPriceCalculation();
    setupToggleBookings();
    
    const bookingForm = document.getElementById("bookingForm");
    if (bookingForm) {
        console.log("Booking form found. Attaching submit listener.");
        document.addEventListener("submit", handleBookingSubmit);
    }
});