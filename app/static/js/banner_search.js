document.addEventListener("DOMContentLoaded", function () {
    const searchButton = document.getElementById("bannerSearchButton");

    // Initialize Flatpickr for the date input
    flatpickr("#bannerSearchDate", {
        dateFormat: "Y-m-d",
        minDate: "today",
        defaultDate: "today",
        disableMobile: true
    });

    if (searchButton) {
        searchButton.addEventListener("click", function () {
            const fromLocation = document.getElementById("bannerSearchFrom").value.trim();
            const toLocation = document.getElementById("bannerSearchTo").value.trim();
            const date = document.getElementById("bannerSearchDate").value;
            const passengers = document.getElementById("bannerSearchPassengers").value;

            // Validation
            if (!fromLocation || !toLocation || !date || passengers <= 0) {
                alert("Please fill in all search fields correctly!");
                return;
            }

            // Redirect to the filter_journeys route with parameters
            const searchParams = new URLSearchParams({
                from: fromLocation,
                to: toLocation,
                date: date,
                passengers: passengers
            });

            window.location.href = `/filter_journeys?${searchParams.toString()}`;
        });
    }
});