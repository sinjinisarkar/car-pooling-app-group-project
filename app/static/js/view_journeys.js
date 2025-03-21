document.addEventListener("DOMContentLoaded", function () {
    const applyBtn = document.getElementById("applyFilters");

    if (applyBtn) {
        applyBtn.addEventListener("click", function () {
            const from = document.getElementById("filterFrom").value.trim();
            const to = document.getElementById("filterTo").value.trim();
            const date = document.getElementById("filterDate").value;
            const category = document.getElementById("filterCategory").value;
            const maxPrice = document.getElementById("filterPrice").value;

            const params = new URLSearchParams();

            if (from) params.append("from", from);
            if (to) params.append("to", to);
            if (date) params.append("date", date);
            if (category && category !== "all") params.append("category", category);
            if (maxPrice) params.append("price", maxPrice);

            window.location.href = `/filter_journeys?${params.toString()}`;
        });
    }
});