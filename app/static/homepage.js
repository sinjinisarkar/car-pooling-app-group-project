document.addEventListener("DOMContentLoaded", function() {
    console.log("DOM fully loaded and parsed");

    // DROPDOWN MENU FUNCTIONALITY 
    const profileBtn = document.getElementById("profile-btn");
    const dropdownMenu = document.getElementById("dropdown-menu");

    if (profileBtn && dropdownMenu) {
        profileBtn.addEventListener("click", function(event) {
            event.stopPropagation(); // Prevent event bubbling
            dropdownMenu.classList.toggle("show");
        });

        // Close dropdown when clicking outside
        document.addEventListener("click", function(event) {
            if (!profileBtn.contains(event.target) && !dropdownMenu.contains(event.target)) {
                dropdownMenu.classList.remove("show");
            }
        });
    } else {
        console.warn("Profile button or dropdown menu not found.");
    }

    // MODAL SWITCHING FUNCTIONALITY
    if (typeof jQuery === "undefined") {
        console.error("Error: jQuery is not loaded. Check if jQuery is properly included.");
        return;
    }

    // Check if modals exist before adding event listeners
    if ($("#loginModal").length && $("#signupModal").length) {
        $("#switchToSignup").click(function(event) {
            event.preventDefault();
            $("#loginModal").modal("hide");
            setTimeout(() => {
                $("#signupModal").modal("show");
            }, 300);
        });

        $("#switchToLogin").click(function(event) {
            event.preventDefault();
            $("#signupModal").modal("hide");
            setTimeout(() => {
                $("#loginModal").modal("show");
            }, 300);
        });
    } else {
        console.warn("Login or Signup modal not found.");
    }

    // ✅ Check if reset password flag exists
    if (sessionStorage.getItem("openLoginModal") === "true") {
        // ✅ Show the login modal
        $("#loginModal").modal("show");

        // ✅ Remove the flag to prevent reopening modal again
        sessionStorage.removeItem("openLoginModal");
    }

});
