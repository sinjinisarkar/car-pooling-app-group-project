document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("platformFeeForm");

    form.addEventListener("submit", function (event) {
        event.preventDefault(); // Stop normal form submission

        const feeInput = document.getElementById("fee").value;
        const url = form.dataset.url;
        
        fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: new URLSearchParams({ fee: feeInput })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message); 
            } else {
                alert("Error: " + data.message); // validation or input error
            }
        })
        .catch(() => {
            alert("Something went wrong while updating the platform fee");
        });
    });
});