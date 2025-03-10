document.addEventListener("DOMContentLoaded", function () {
    const showUpcoming = document.getElementById("showUpcoming");
    const showPublished = document.getElementById("showPublished");
    const upcomingSection = document.getElementById("upcomingSection");
    const publishedSection = document.getElementById("publishedSection");
    const toggleInactive = document.getElementById("toggleInactive");
    const inactiveSection = document.getElementById("inactiveSection");

    if (showUpcoming && showPublished && upcomingSection && publishedSection) {
        showUpcoming.addEventListener("click", function () {
            upcomingSection.style.display = "block";
            publishedSection.style.display = "none";
            showUpcoming.classList.add("active");
            showPublished.classList.remove("active");
        });

        showPublished.addEventListener("click", function () {
            upcomingSection.style.display = "none";
            publishedSection.style.display = "block";
            showPublished.classList.add("active");
            showUpcoming.classList.remove("active");
        });
    }

    if (toggleInactive && inactiveSection) {
        toggleInactive.addEventListener("click", function () {
            if (inactiveSection.style.display === "none") {
                inactiveSection.style.display = "block";
                toggleInactive.textContent = "Hide Inactive Bookings";
            } else {
                inactiveSection.style.display = "none";
                toggleInactive.textContent = "Show Inactive Bookings";
            }
        });
    }
});