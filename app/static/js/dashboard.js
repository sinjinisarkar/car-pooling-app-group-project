document.addEventListener("DOMContentLoaded", function () {
    
    const showUpcoming = document.getElementById("showUpcoming");
    const showPublished = document.getElementById("showPublished");
    const showSavedCards = document.getElementById("showSavedCards");
    const showEarnings = document.getElementById("showEarnings");

    const upcomingSection = document.getElementById("upcomingSection");
    const publishedSection = document.getElementById("publishedSection");
    const savedCardsSection = document.getElementById("savedCardsSection");
    const earningsSection = document.getElementById("earningsSection");
    
    const toggleInactive = document.getElementById("toggleInactive");
    const inactiveSection = document.getElementById("inactiveSection");

    upcomingSection.style.display = "block";
    publishedSection.style.display = "none";
    savedCardsSection.style.display = "none";
    inactiveSection.style.display = "none"; // Ensure inactive section is hidden at start
    showUpcoming.classList.add("active");

    if (showUpcoming && showPublished && showSavedCards && showEarnings) {
        showUpcoming.addEventListener("click", function () {
            upcomingSection.style.display = "block";
            publishedSection.style.display = "none";
            savedCardsSection.style.display = "none";
            earningsSection.style.display = "none";
            showUpcoming.classList.add("active");
            showPublished.classList.remove("active");
            showSavedCards.classList.remove("active");
            showEarnings.classList.remove("active");
        });

        showPublished.addEventListener("click", function () {
            upcomingSection.style.display = "none";
            publishedSection.style.display = "block";
            savedCardsSection.style.display = "none";
            earningsSection.style.display = "none";
            inactiveSection.style.display = "none";
            showPublished.classList.add("active");
            showUpcoming.classList.remove("active");
            showSavedCards.classList.remove("active");
            showEarnings.classList.remove("active");
        });

        showSavedCards.addEventListener("click", function () {
            upcomingSection.style.display = "none";
            publishedSection.style.display = "none";
            savedCardsSection.style.display = "block";
            earningsSection.style.display = "none";
            inactiveSection.style.display = "none";
            showSavedCards.classList.add("active");
            showUpcoming.classList.remove("active");
            showPublished.classList.remove("active");
            showEarnings.classList.remove("active");
        });

        showEarnings.addEventListener("click", function () {
            upcomingSection.style.display = "none";
            publishedSection.style.display = "none";
            savedCardsSection.style.display = "none";
            earningsSection.style.display = "block";
            inactiveSection.style.display = "none";
            showEarnings.classList.add("active");
            showUpcoming.classList.remove("active");
            showPublished.classList.remove("active");
            showSavedCards.classList.remove("active");

            if (typeof animateEarnings === "function") {
                animateEarnings();
            }
        });
    }

    if (toggleInactive && inactiveSection) {
        toggleInactive.addEventListener("click", function () {
            if (upcomingSection.style.display === "block") {
                if (inactiveSection.style.display === "none") {
                    inactiveSection.style.display = "block";
                    toggleInactive.textContent = "Hide Inactive Bookings";
                } else {
                    inactiveSection.style.display = "none";
                    toggleInactive.textContent = "Show Inactive Bookings";
                }
            }
        });
    }

    // Delete Card Functionality
    document.querySelectorAll(".delete-card-btn").forEach(button => {
        button.addEventListener("click", function () {
            const cardId = this.getAttribute("data-card-id");

            if (confirm("Are you sure you want to delete this card?")) {
                fetch(`/delete_saved_card/${cardId}`, {
                    method: "DELETE",
                    headers: { "Content-Type": "application/json" }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert("Card deleted successfully!");
                        location.reload();
                    } else {
                        alert("Failed to delete card. Please try again.");
                    }
                })
                .catch(error => {
                    console.error("Error:", error);
                    alert("An error occurred. Please try again.");
                });
            }
        });
    });
});