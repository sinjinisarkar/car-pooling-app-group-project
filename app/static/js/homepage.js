document.addEventListener("DOMContentLoaded", function () {
    console.log("loaded homepage.js")
    function switchModal(hideModalId, showModalId) {
        if (!$(hideModalId).hasClass("show")) {
            // If the first modal is not actually visible, just show the second modal immediately
            $(showModalId).modal("show");
        } else {
            // Otherwise, hide the first modal and show the second only after it's fully hidden
            $(hideModalId).modal("hide");
            $(hideModalId).on("hidden.bs.modal", function () {
                $(showModalId).modal("show");
                $(hideModalId).off("hidden.bs.modal"); // Prevent duplicate event bindings
            });
        }
    }

    // Switch from Login to Signup
    document.getElementById("switchToSignup").addEventListener("click", function (event) {
        event.preventDefault();
        switchModal("#loginModal", "#signupModal");
    });

    // Switch from Signup to Login
    document.getElementById("switchToLogin").addEventListener("click", function (event) {
        event.preventDefault();
        switchModal("#signupModal", "#loginModal");
    });
});