document.addEventListener("DOMContentLoaded", function () {
    event.preventDefault();
    
    const rideIdElement = document.getElementById("ride_id");
    const seatsElement = document.getElementById("seats");
    const totalPriceElement = document.getElementById("total_price");

    console.log("Checking ride details...");
    console.log("Ride ID Element:", rideIdElement);
    console.log("Seats Element:", seatsElement);
    console.log("Total Price Element:", totalPriceElement);

    if (!rideIdElement || !seatsElement || !totalPriceElement) {
        console.error(" Missing form elements in the HTML! Check payment.html");
        return;
    }

    const rideId = rideIdElement.value || "0";
    const seats = seatsElement.value || "0";
    const totalPrice = totalPriceElement.value || "0.00";

    console.log(" Ride ID:", rideId);
    console.log(" Seats:", seats);
    console.log(" Total Price:", totalPrice);

    if (!rideId || !seats || !totalPrice) {
        console.error("Missing ride details. Cannot proceed.");
        return;
    }

    // Handle Payment Form Submission
    document.getElementById("paymentForm").addEventListener("submit", function (event) {
        event.preventDefault(); // Prevent normal form submission

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
                alert("Payment successful! Redirecting...");
                console.log("Redirecting to:", data.redirect_url); // Debugging print
                window.location.href = data.redirect_url; // Redirect to dashboard
            } else {
                alert(data.message || "Payment failed! Please try again.");
            }
        })
        .catch(error => {
            console.error(" Payment error:", error);
            alert("An error occurred while processing your payment.");
        });
    });
});
