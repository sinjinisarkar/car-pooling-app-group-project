document.addEventListener("DOMContentLoaded", function () {
    console.log("Auth.js loaded!");

    // AJAX: Handle User Signup
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

    // AJAX: Handle User Login
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

    // ✅ AJAX: Handle User Logout
    $("#logout-btn").click(function (event) {
        event.preventDefault();

        $.ajax({
            type: "POST",
            url: "/logout",
            success: function (response) {
                alert(response.message);
                location.reload(); // Refresh page after logout
            },
            error: function (xhr) {
                alert("Logout failed.");
            },
        });
    });
});
