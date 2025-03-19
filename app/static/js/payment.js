document.addEventListener("DOMContentLoaded", function () {

    // Get tab elements
    const savedCardTab = document.getElementById("savedCardTab");
    const manualCardTab = document.getElementById("manualCardTab");
    const savedCardSection = document.getElementById("savedCardSection");
    const manualCardSection = document.getElementById("manualCardSection");

    // Get saved card elements
    const payWithSavedCardButton = document.getElementById("payWithSavedCard");

    // Get manual card form elements
    const paymentForm = document.getElementById("paymentForm");
    const cardNumberInput = document.getElementById("card_number");
    const expiryInput = document.getElementById("expiry");
    const cardholderNameInput = document.getElementById("cardholder_name");
    const cvvInput = document.getElementById("cvv");
    const saveCardCheckbox = document.getElementById("save_card");

    // Default Tab Selection
    savedCardTab.classList.add("active");
    savedCardSection.style.display = "block";
    manualCardSection.style.display = "none";

    // Tab Switching
    savedCardTab.addEventListener("click", function (event) {
        event.preventDefault();
        savedCardTab.classList.add("active");
        manualCardTab.classList.remove("active");
        savedCardSection.style.display = "block";
        manualCardSection.style.display = "none";
    });

    manualCardTab.addEventListener("click", function (event) {
        event.preventDefault();
        manualCardTab.classList.add("active");
        savedCardTab.classList.remove("active");
        savedCardSection.style.display = "none";
        manualCardSection.style.display = "block";
    });


    // Handle Saved Card Payment
    payWithSavedCardButton.addEventListener("click", function () {
        const rideId = document.getElementById("ride_id").value;
        const seats = document.getElementById("seats").value;
        const totalPrice = document.getElementById("total_price").value;
        const selectedCard = document.querySelector('input[name="saved_card"]:checked')?.value;

        if (!selectedCard) {
            alert("Please select a saved card.");
            return;
        }

        let urlParams = new URLSearchParams(window.location.search);
        let selectedDates = urlParams.getAll("selected_dates");
        let confirmationEmail = urlParams.get("email"); 

        if (selectedDates.length === 0) {
            let singleDate = urlParams.get("selected_date");
            if (singleDate) {
                selectedDates = [singleDate];
            }
        }

        if (!selectedDates.length) {
            alert("Error: No selected dates found! Please try again.");
            return;
        }

        const paymentData = {
            ride_id: rideId,
            seats: seats,
            total_price: totalPrice,
            selected_dates: selectedDates,
            email: confirmationEmail,
            use_saved_card: true,
            saved_card_id: selectedCard
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

    
    // Handle Manual Card Payment
    paymentForm.addEventListener("submit", function (event) {
        event.preventDefault();

        const rideId = document.getElementById("ride_id").value;
        const seats = document.getElementById("seats").value;
        const totalPrice = document.getElementById("total_price").value;
        const cardNumber = cardNumberInput.value;
        const expiry = expiryInput.value;
        const cvv = cvvInput.value;
        const cardholderName = cardholderNameInput.value;
        const saveCard = saveCardCheckbox.checked;

        let urlParams = new URLSearchParams(window.location.search);
        let selectedDates = urlParams.getAll("selected_dates");
        let confirmationEmail = urlParams.get("email"); 

        if (selectedDates.length === 0) {
            let singleDate = urlParams.get("selected_date");
            if (singleDate) {
                selectedDates = [singleDate];
            }
        }

        if (!selectedDates.length) {
            alert("Error: No selected dates found! Please try again.");
            return;
        }

        const paymentData = {
            ride_id: rideId,
            seats: seats,
            total_price: totalPrice,
            selected_dates: selectedDates,
            email: confirmationEmail,
            use_saved_card: false,
            card_number: cardNumber,
            expiry: expiry,
            cvv: cvv,
            cardholder_name: cardholderName,
            save_card: saveCard
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