document.addEventListener("DOMContentLoaded", function () {
    console.log("Auth.js loaded!");

    // Handle User Signup
    $("#signupForm").submit(function (event) {
        event.preventDefault(); // Prevent normal form submission

        let userData = {
            username: $("#signup-name").val(),
            email: $("#signup-email").val(),
            password: $("#signup-password").val(),
            confirm_password: $("#signupConfirmPassword").val(),
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
                    alert(xhr.responseJSON?.message || "An unexpected error occurred. Please try again.");
                }
            },
        });
    });
});
