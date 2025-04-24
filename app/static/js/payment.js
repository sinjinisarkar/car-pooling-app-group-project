document.addEventListener("DOMContentLoaded", function () {

    const savedCardTab = document.getElementById("savedCardTab");
    const manualCardTab = document.getElementById("manualCardTab");
    const savedCardSection = document.getElementById("savedCardSection");
    const manualCardSection = document.getElementById("manualCardSection");
    const payWithSavedCardButton = document.getElementById("payWithSavedCard");

    // manual card form elements
    const paymentForm = document.getElementById("paymentForm");
    const cardNumberInput = document.getElementById("card_number");
    const expiryInput = document.getElementById("expiry");
    const cardholderNameInput = document.getElementById("cardholder_name");
    const cvvInput = document.getElementById("cvv");
    const saveCardCheckbox = document.getElementById("save_card");

    // default tab
    savedCardTab.classList.add("active");
    savedCardSection.style.display = "block";
    manualCardSection.style.display = "none";

    // tab switching
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

    // validation functions for card details
    function isValidExpiryDate(expiry) {
        const regex = /^(0[1-9]|1[0-2])\/\d{2}$/;
        if (!regex.test(expiry)) return false;

        const [month, year] = expiry.split("/").map(Number);
        const currentDate = new Date();
        const currentYear = currentDate.getFullYear() % 100;
        const currentMonth = currentDate.getMonth() + 1;

        return year > currentYear || (year === currentYear && month >= currentMonth);
    }

    function isValidCardNumber(cardNumber) {
        return /^\d{16}$/.test(cardNumber);
    }

    function isValidCVV(cvv) {
        return /^\d{3}$/.test(cvv);
    }

    function isValidCardholderName(name) {
        return /^[A-Za-z\s]+$/.test(name);
    }

    // handling payments via saved card option
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

        // go to process payment route
        fetch("/process_payment", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(paymentData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert("Booking confirmation email sent!");
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

    // handling payment via manual form
    paymentForm.addEventListener("submit", function (event) {
        event.preventDefault();

        const rideId = document.getElementById("ride_id").value;
        const seats = document.getElementById("seats").value;
        const totalPrice = document.getElementById("total_price").value;
        const cardNumber = cardNumberInput.value;
        const expiry = expiryInput.value.trim();
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

        // checking that all the details are entered valid
        if (!isValidExpiryDate(expiry)) {
            alert("Invalid expiry date. Please enter a valid MM/YY format and ensure the card is not expired.");
            return;
        }
        if (!isValidCardNumber(cardNumber)) {
            alert("Invalid card number. Please enter a 16-digit card number.");
            return;
        }
        if (!isValidCVV(cvv)) {
            alert("Invalid CVV. Please enter a 3-digit CVV.");
            return;
        }
        if (!isValidCardholderName(cardholderName)) {
            alert("Invalid cardholder name. Only letters and spaces are allowed.");
            return;
        }
        // check if the manually entered card is already saved
        if (saveCard) {
            const lastFour = cardNumber.slice(-4);
            const savedCardLabels = document.querySelectorAll("#savedCardSection .form-check-label");
        
            for (let label of savedCardLabels) {
                const labelText = label.textContent;
                if (
                    labelText.includes(`**** ${lastFour}`) &&
                    labelText.includes(`Exp: ${expiry}`)
                ) {
                    const confirmSave = confirm("A card with the same last 4 digits and expiry is already saved. Do you still want to save this one?");
                    if (!confirmSave) return;
                    break; // allow to continue
                }
            }
        }

        // go to process payment route
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