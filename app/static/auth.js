document.addEventListener("DOMContentLoaded", function () {
    console.log("Auth.js loaded!");

    // Function to validate password strength
    function validatePassword(password) {
        const specialCharacterRegex = /[!@#$%^&*(),.?":{}|<>]/;
        if (password.length < 8) {
            alert("Password must be at least 8 characters long with at least one special character.");
            return false;
        }
        if (!specialCharacterRegex.test(password)) {
            alert("Password must be at least 8 characters long with at least one special character.");
            return false;
        }
        return true;
    }

    // Handle User Signup with frontend validation
    $("#signupForm").submit(function (event) {
        event.preventDefault(); // Prevent normal form submission

        let password = $("#signup-password").val();
        let confirmPassword = $("#signupConfirmPassword").val();

        // Frontend password validation
        if (!validatePassword(password)) {
            return; // Stop submission if password is weak
        }

        if (password !== confirmPassword) {
            alert("Passwords do not match.");
            return; // Stop submission if passwords don't match
        }

        let userData = {
            username: $("#signup-name").val(),
            email: $("#signup-email").val(),
            password: password,
            confirm_password: confirmPassword,
        };

        $.ajax({
            type: "POST",
            url: "/register",
            contentType: "application/json",
            data: JSON.stringify(userData),
            success: function (response) {
                alert(response.message);
                $("#signupModal").modal("hide");
                $("#loginModal").modal("show");
            },
            error: function (xhr) {
                alert(xhr.responseJSON.message || "Signup failed.");
            },
        });
    });

    // Handle User Login
    $("#loginForm").submit(function (event) {
        event.preventDefault(); // Prevent normal form submission

        const loginData = {
            email: $("#login-email").val(),
            password: $("#login-password").val(),
        };

        $.ajax({
            type: "POST",
            url: "/login",
            contentType: "application/json",
            data: JSON.stringify(loginData),
            success: function (response) {
                alert(response.message);
                $("#loginModal").modal("hide");
                location.reload(); // Refresh page after login
            },
            error: function (xhr) {
                alert(xhr.responseJSON.message || "Login failed.");
            },
        });
    });

    // Handle User Logout
    $("#logout-form").click(function (event) {
        event.preventDefault();

        $.ajax({
            type: "POST",
            url: "/logout",
            success: function (response) {
                alert(response.message);
                window.location.href = "/"; // Redirect to home after logout
            },
            error: function (xhr) {
                alert("Logout failed.");
            },
        });
    });

    // Handle "Publish a Ride" Click
    $("#publish-ride-btn").click(function (event) {
        event.preventDefault(); // Prevent default link behavior

        $.ajax({
            type: "GET",
            url: "/publish_ride",
            success: function (response) {
                // If user is logged in, redirect to publish page
                window.location.href = "/publish_ride";
            },
            error: function (xhr) {
                if (xhr.status === 401) {
                    // If user is not logged in, show signup modal
                    $("#signupModal").modal("show");
                } else {
                    alert(xhr.responseJSON?.message || "You need to log in before publishing a ride.");
                }
            },
        });
    });
});


// Show and hide password
document.addEventListener("DOMContentLoaded", function () {
    console.log("Auth.js loaded!");

    function togglePassword(inputId, iconId) {
        const passwordInput = document.getElementById(inputId);
        const toggleIcon = document.getElementById(iconId);

        if (!passwordInput || !toggleIcon) {
            console.log(`Element not found: ${inputId} or ${iconId}`);
            return;
        }

        if (passwordInput.type === "password") {
            passwordInput.type = "text";
            toggleIcon.innerHTML = "👁‍🗨️"; // Eye closed
        } else {
            passwordInput.type = "password";
            toggleIcon.innerHTML = "👁️"; // Eye open
        }
    }

    // Attach click event listeners dynamically
    document.querySelectorAll(".toggle-password").forEach(function (toggleIcon) {
        toggleIcon.addEventListener("click", function () {
            // Find the closest input within the same .input-group
            const inputField = this.closest(".input-group").querySelector("input");
            if (inputField) {
                togglePassword(inputField.id, this.id);
            }
        });
    });
});
