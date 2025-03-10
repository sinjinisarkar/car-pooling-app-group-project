document.addEventListener("DOMContentLoaded", function () {
    const showUpcoming = document.getElementById("showUpcoming");
    const showPublished = document.getElementById("showPublished");
    const upcomingSection = document.getElementById("upcomingSection");
    const publishedSection = document.getElementById("publishedSection");

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
});