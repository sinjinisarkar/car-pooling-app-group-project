document.addEventListener("DOMContentLoaded", function () {
    // Ensure Ride Details Are Loaded
    const rideId = document.getElementById("ride_id").value;
    const seats = document.getElementById("seats").value;
    const totalPrice = document.getElementById("total_price").value;

    if (!rideId || !seats || !totalPrice) {
        console.error("❌ Missing ride details. Cannot proceed.");
        return;
    }

    // Handle Payment Form Submission
    document.getElementById("paymentForm").addEventListener("submit", function (event) {
        event.preventDefault(); // ✅ Prevent normal form submission

        const paymentData = {
            ride_id: rideId,
            seats: seats,
            total_price: totalPrice,
            card_number: document.getElementById("card_number").value,
            expiry: document.getElementById("expiry").value,
            cvv: document.getElementById("cvv").value
        };

        fetch("/process_payment", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(paymentData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("✅ Payment successful! Redirecting...");
                window.location.href = data.redirect_url; // Redirect to dashboard
            } else {
                alert(data.message || "❌ Payment failed! Please try again.");
            }
        })
        .catch(error => {
            console.error("❌ Payment error:", error);
            alert("❌ An error occurred while processing your payment.");
        });
    });
});
