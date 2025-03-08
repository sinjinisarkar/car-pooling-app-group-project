document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("searchInput");
    const searchButton = document.getElementById("searchButton");
    const resultsContainer = document.getElementById("searchResults");
    

    // ✅ Open Modal When Search Bar is Clicked
    if (searchInput) {
        searchInput.addEventListener("click", function () {
            const searchModal = new bootstrap.Modal(document.getElementById("searchModal"));
            searchModal.show();
        });
    }

    // ✅ Perform Search When Clicking "Search"
    if (searchButton) {
        searchButton.addEventListener("click", function () {
            const fromLocation = document.getElementById("searchFrom").value.trim();
            const toLocation = document.getElementById("searchTo").value.trim();
            const date = document.getElementById("searchDate").value;
            const passengers = document.getElementById("searchPassengers").value;

            if (!fromLocation || !toLocation || !date || passengers <= 0) {
                alert("❌ Please fill in all search fields correctly!");
                return;
            }

            // 🚀 Send Search Request to Backend
            fetch(`/search_journeys?from=${fromLocation}&to=${toLocation}&date=${date}&passengers=${passengers}`)
                .then(response => response.json())
                .then(data => {
                    console.log("🚀 Search Results:", data);
                    displaySearchResults(data.journeys);
                })
                .catch(error => console.error("❌ Error fetching search results:", error));
        });
    }

    // ✅ Function to Display Search Results in the Modal
    function displaySearchResults(journeys) {
        resultsContainer.innerHTML = "";

        if (journeys.length === 0) {
            resultsContainer.innerHTML = "<p class='text-center text-danger'>No journeys found.</p>";
            return;
        }

        journeys.forEach(journey => {
            const journeyCard = document.createElement("div");
            journeyCard.classList.add("journey-card", "p-3", "mb-3", "border", "rounded", "shadow-sm");
            journeyCard.innerHTML = `
                <h5>${journey.from} → ${journey.to}</h5>
                <p><strong>Date:</strong> ${journey.date} | <strong>Time:</strong> ${journey.time}</p>
                <p><strong>Seats Available:</strong> ${journey.seats_available} | <strong>Price:</strong> £${journey.price_per_seat}</p>
                <button class="btn btn-primary w-100" onclick="bookRide(${journey.id})">Book Now</button>
            `;
            resultsContainer.appendChild(journeyCard);
        });
    }
});

// ✅ Function to Redirect to Booking Page
function bookRide(rideId) {
    window.location.href = `/book_journey/${rideId}`;
}
