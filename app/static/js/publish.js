document.addEventListener("DOMContentLoaded", function () {

    // date and time picker for one-time journey
    if (document.querySelector("#date_time")) {
        flatpickr("#date_time", {
            enableTime: true,
            dateFormat: "Y-m-d H:i",
            minDate: "today",
            defaultDate: "today",
            disableMobile: false
        });
    }

    // recurring dates picker for commuting journeys
    if (document.querySelector("#recurrence_dates")) {
        flatpickr("#recurrence_dates", {
            mode: "multiple",
            dateFormat: "Y-m-d",
            minDate: "today",
            defaultDate: "today",
            disableMobile: false
        });
    }
    // commute time picker for commuting journeys
    if (document.querySelector("#commute_times")) {
        flatpickr("#commute_times", {
            enableTime: true,
            noCalendar: true,
            mode: "multiple",
            dateFormat: "H:i",
            disableMobile: false
        });
    }

    // category selection (one-time or commuting)
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

    // update UI on category change
    updateUI();
    categorySelect?.addEventListener("change", updateUI);

    // price validation
    const priceInput = document.getElementById("price_per_seat");

});