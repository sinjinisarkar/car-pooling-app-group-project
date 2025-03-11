document.addEventListener("DOMContentLoaded", function () {
    console.log("🚀 Initializing Flatpickr for Publish Ride Page...");

    // Date & Time Picker for One-Time Ride
    if (document.querySelector("#date_time")) {
        flatpickr("#date_time", {
            enableTime: true,
            dateFormat: "Y-m-d H:i",
            minDate: "today",
            defaultDate: "today",
            disableMobile: false
        });
    }

    // Recurring Dates Picker for Commuting Rides
    if (document.querySelector("#recurrence_dates")) {
        flatpickr("#recurrence_dates", {
            mode: "multiple",
            dateFormat: "Y-m-d",
            minDate: "today",
            defaultDate: "today",
            disableMobile: false
        });
    }

    // Commute Times Picker for Commuting Rides
    if (document.querySelector("#commute_times")) {
        flatpickr("#commute_times", {
            enableTime: true,
            noCalendar: true,
            mode: "multiple",
            dateFormat: "H:i",
            disableMobile: false
        });
    }

    // Category Selection Logic (Show/Hide Fields Dynamically)
    const categorySelect = document.getElementById("category");
    const dateTimeDiv = document.getElementById("date_time_div");
    const recurrenceSection = document.getElementById("recurrence_section");
    const commuteTimesSection = document.getElementById("commute_times_section");

    function updateUI() {
        if (!categorySelect) return;

        const isOneTime = categorySelect.value === "one-time";
        dateTimeDiv.style.display = isOneTime ? "block" : "none";
        recurrenceSection.style.display = isOneTime ? "none" : "block";
        commuteTimesSection.style.display = isOneTime ? "none" : "block";
    }

    // Apply UI updates on page load and on category change
    updateUI();
    categorySelect?.addEventListener("change", updateUI);
});