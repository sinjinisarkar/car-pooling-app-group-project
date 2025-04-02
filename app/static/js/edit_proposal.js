document.addEventListener("DOMContentLoaded", () => {
    const proposalForm = document.getElementById("proposalForm");
    const pickupInput = document.getElementById("newPickup");
    const timeInput = document.getElementById("newTime");
    const costInput = document.getElementById("newCost");

    proposalForm.addEventListener("submit", function (e) {
        e.preventDefault();

        const bookingId = window.location.pathname.split("/").pop();  // /chat/<booking_id>
        const proposedData = {
            booking_id: bookingId,
            pickup: pickupInput.value.trim(),
            time: timeInput.value.trim(),
            cost: costInput.value.trim()
        };

        // Filter out empty values
        for (let key in proposedData) {
            if (proposedData[key] === "") {
                delete proposedData[key];
            }
        }

        fetch("/propose_edit", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(proposedData)
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert("Edit proposal sent!");
                pickupInput.value = "";
                timeInput.value = "";
                costInput.value = "";
                $('#proposalModal').modal('hide');
            } else {
                alert("Failed to send proposal.");
            }
        });
    });

    // Optional: Reset form on modal close
    $('#proposalModal').on('hidden.bs.modal', function () {
        proposalForm.reset();
    });
});