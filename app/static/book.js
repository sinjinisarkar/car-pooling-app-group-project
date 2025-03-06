document.addEventListener("DOMContentLoaded", function () {
    // Toggle Date & Time or Recurrence Days based on category selection
    let categorySelect = document.getElementById("category");
    let dateTimeDiv = document.getElementById("date_time_div");
    let recurrenceDiv = document.getElementById("recurrence_days");
    let dateTimeInput = document.getElementById("date_time");

    if (categorySelect && dateTimeDiv && recurrenceDiv) {
        categorySelect.addEventListener("change", function () {
            if (categorySelect.value === "commuting") {
                dateTimeDiv.style.display = "none";  // Hide Date & Time
                recurrenceDiv.style.display = "block";  // Show Recurrence Days
                if (dateTimeInput) {
                    dateTimeInput.value = "";  // Clear Date & Time input
                }
            } else {
                dateTimeDiv.style.display = "block";  // Show Date & Time
                recurrenceDiv.style.display = "none";  // Hide Recurrence Days
            }
        });
    }

    // Ensure recurrence days are properly formatted when submitting the form
    let form = document.querySelector("form");
    if (form) {
        form.addEventListener("submit", function (event) {
            if (categorySelect.value === "commuting") {
                let selectedDays = [];
                document.querySelectorAll('input[name="recurrence_days"]:checked').forEach(checkbox => {
                    selectedDays.push(checkbox.value);
                });

                if (selectedDays.length === 0) {
                    event.preventDefault();  // Prevent form submission if no days selected
                    alert("Please select at least one recurrence day.");
                    return;
                }

                // Create a hidden input field to store selected recurrence days as a comma-separated string
                let recurrenceInput = document.createElement("input");
                recurrenceInput.type = "hidden";
                recurrenceInput.name = "recurrence_days";
                recurrenceInput.value = selectedDays.join(",");
                form.appendChild(recurrenceInput);
            }
        });
    }

    // Calculate total price dynamically when seat selection changes
    let seatsInput = document.getElementById("seats");
    let totalPriceInput = document.getElementById("total_price");
    let pricePerSeatElement = document.getElementById("price_per_seat");

    if (seatsInput && totalPriceInput && pricePerSeatElement) {
        let pricePerSeat = parseFloat(pricePerSeatElement.dataset.price);
        seatsInput.addEventListener("input", function () {
            const seats = parseInt(this.value);
            if (!isNaN(seats) && seats > 0) {
                const totalPrice = seats * pricePerSeat;
                totalPriceInput.value = totalPrice.toFixed(2);
            } else {
                totalPriceInput.value = "0.00";  // Default if no seats selected
            }
        });
    }

    // Toggle booked rides on demand
    let toggleBookingsBtn = document.getElementById("toggleBookings");
    let bookingsContainer = document.getElementById("bookingsContainer");

    if (toggleBookingsBtn && bookingsContainer) {
        toggleBookingsBtn.addEventListener("click", function () {
            bookingsContainer.style.display = (bookingsContainer.style.display === "none") ? "block" : "none";
        });
    }
});
