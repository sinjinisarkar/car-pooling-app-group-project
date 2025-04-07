document.addEventListener("DOMContentLoaded", function () {
    // Function to show popup messages
    function showPopup(message) {
        alert(message); 
    }

    // Handle Forgot Password Form Submission
    $("#forgotPasswordForm").submit(function (event) {
        event.preventDefault();

        let email = $("#forgotPasswordEmail").val();

        if (!email) {
            showPopup("Please enter your email address.");
            return;
        }

        $.ajax({
            type: "POST",
            url: "/forgot-password",
            contentType: "application/json",  
            data: JSON.stringify({ email: email }),  
            success: function (response) {
                showPopup(response.message);
            },
            error: function (xhr) {
                showPopup(xhr.responseJSON?.message || "Error processing request.");
            },
        });
    });

    // Handle Reset Password Form Submission
    $("#resetPasswordForm").submit(function (event) {
        event.preventDefault();

        let newPassword = $("#newPassword").val();
        let confirmPassword = $("#confirmPassword").val();
        let resetToken = $("#resetToken").val();  
        let userId = $("#resetUserId").val();

        if (!newPassword || !confirmPassword) {
            showPopup("Please enter a new password.");
            return;
        }

        if (newPassword !== confirmPassword) {
            showPopup("Passwords do not match!");
            return;
        }

        $.ajax({
            type: "POST",
            url: `/reset-password/${resetToken}/${userId}`, 
            contentType: "application/json",  
            data: JSON.stringify({ token: resetToken, user_id: userId, password: newPassword }),  
            success: function (response) {
                showPopup(response.message);

                // Store a sessionStorage flag to open login modal
                sessionStorage.setItem("openLoginModal", "true");

                // Check if the tab was opened from an email link
                if (window.opener) {
                    // Close the reset password tab
                    window.close();
                    // Redirect the original tab to the homepage
                    window.opener.location.href = "/";
                } else {
                    // If no parent tab, just redirect normally
                    window.location.href = "/";
                }
            },
            error: function (xhr) {
                showPopup(xhr.responseJSON?.message || "Error resetting password.");
            },
        });
    });
});
