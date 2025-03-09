document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("paymentForm").addEventListener("submit", function (event) {
        event.preventDefault(); // Prevent normal form submission

        const rideId = document.getElementById("ride_id").value;
        const seats = document.getElementById("seats").value;
        const totalPrice = document.getElementById("total_price").value;
        const cardNumber = document.getElementById("card_number").value;
        const expiry = document.getElementById("expiry").value;
        const cvv = document.getElementById("cvv").value;

        // ✅ Fix: Get all selected dates properly
        let urlParams = new URLSearchParams(window.location.search);
        let selectedDates = urlParams.getAll("selected_dates");  // ✅ Get all values as an array
        let confirmationEmail = urlParams.get("email"); 

        // ✅ If no dates found, check `selected_date` (singular)
        if (selectedDates.length === 0) {
            let singleDate = urlParams.get("selected_date");
            if (singleDate) {
                selectedDates = [singleDate];
            }
        }

        console.log("Extracted selected dates:", selectedDates);

        if (!selectedDates.length) {
            alert("Error: No selected dates found! Please try again.");
            return;
        }

        const paymentData = {
            ride_id: rideId,
            seats: seats,
            total_price: totalPrice,
<<<<<<< HEAD
            card_number: document.getElementById("card_number").value,
            expiry: document.getElementById("expiry").value,
            cvv: document.getElementById("cvv").value,
            selected_date: selectedDate,  
=======
            card_number: cardNumber,
            expiry: expiry,
            cvv: cvv,
            selected_dates: selectedDates,  // ✅ Now always an array
>>>>>>> origin/main
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