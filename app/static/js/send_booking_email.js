document.addEventListener("DOMContentLoaded", function () {
    const resendButtons = document.querySelectorAll(".resend-email-btn");

    resendButtons.forEach(button => {
        button.addEventListener("click", function () {
            const bookingId = this.dataset.bookingId;
            
            fetch(`/resend_booking_confirmation/${bookingId}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert("Booking confirmation email resent!");
                } else {
                    alert("Failed to resend email. Please try again later.");
                }
            })
            .catch(error => {
                console.error("Error:", error);
                alert("An error occurred while resending the email.");
            });
        });
    });
});
