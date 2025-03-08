document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("paymentForm").addEventListener("submit", function (event) {
        event.preventDefault(); // Prevent normal form submission

        const rideId = document.getElementById("ride_id").value;
        const seats = document.getElementById("seats").value;
        const totalPrice = document.getElementById("total_price").value;
        const cardNumber = document.getElementById("card_number").value;
        const expiry = document.getElementById("expiry").value;
        const cvv = document.getElementById("cvv").value;

        // ✅ Fix: Get selected date properly
        let urlParams = new URLSearchParams(window.location.search);
        let selectedDate = urlParams.get("selected_date"); 
        let confirmationEmail = urlParams.get("email"); 

        console.log("Extracted selected date:", selectedDate);

        if (!selectedDate || selectedDate === "None") {
            alert("Error: No selected date found! Please try again.");
            return;
        }

        const paymentData = {
            ride_id: rideId,
            seats: seats,
            total_price: totalPrice,
            card_number: cardNumber,
            expiry: expiry,
            cvv: cvv,
            selected_dates: [selectedDate],  // ✅ Ensure this is always an array
            email: confirmationEmail  
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
                window.location.href = data.redirect_url; 
            } else {
                alert(data.message || "Payment failed! Please try again.");
            }
        })
        .catch(error => {
            console.error("Payment error:", error);
            alert("An error occurred while processing your payment.");
        });
    });
});
