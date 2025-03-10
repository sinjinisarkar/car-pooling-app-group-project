document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".cancel-btn").forEach(button => {
        button.addEventListener("click", function () {
            const bookingId = this.dataset.bookingId;
            const price = parseFloat(this.dataset.price);
            const rideDate = new Date(this.dataset.date);
            const now = new Date();
            const timeDifference = (rideDate - now) / (1000 * 60); // Minutes difference

            console.log("🔍 Button Clicked: ", this);
            console.log("🔍 Retrieved Booking ID: ", bookingId);
            console.log("🔍 Ride Date: ", rideDate);
            console.log("🔍 Price: ", price);

            let refundMessage = "";
            if (timeDifference < 15) {
                const cancellationFee = (price * 0.75).toFixed(2);
                const refundAmount = (price - cancellationFee).toFixed(2);
                refundMessage = `⚠️ If you cancel now, you will be charged a 75% cancellation fee (£${cancellationFee}). Refund: £${refundAmount}.`;
            } else {
                refundMessage = "✅ You are eligible for a full refund.";
            }

            console.log("🔍 Cancel Booking Request for Booking ID:", bookingId);
            // Show confirmation alert
            if (confirm(`Are you sure you want to cancel this ride? \n\n${refundMessage}`)) {
                // ✅ Send POST request instead of redirecting with GET
                fetch(`/cancel_booking/${bookingId}`, { 
                    method: "POST",
                    headers: { "Content-Type": "application/json" }
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    if (data.success) {
                        location.reload();  // ✅ Refresh the page after successful cancellation
                    }
                })
                .catch(error => {
                    console.error("Cancellation error:", error);
                    alert(`An error occurred while canceling the ride: ${error.message}`);
                });
            }
        });
    });
});