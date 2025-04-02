document.addEventListener("DOMContentLoaded", () => {
    // Extract bookingId and currentUser from HTML data attributes
    const chatBox = document.getElementById("chat-box");
    const chatForm = document.getElementById("chat-form");
    const messageInput = document.getElementById("message-input");

    // Grab values directly from the URL and hidden elements
    const urlParts = window.location.pathname.split("/");
    const bookingId = urlParts[urlParts.length - 1]; // last segment in /chat/<booking_id>

    // You could store this in a hidden element via Jinja in future, but for now:
    const currentUser = document.querySelector("meta[name='current-user']").content;

    // Load existing messages
    function loadMessages() {
        fetch(`/get_messages/${bookingId}`)
            .then(res => res.json())
            .then(data => {
                chatBox.innerHTML = "";
                data.forEach(msg => {
                    const messageDiv = document.createElement("div");
                    messageDiv.classList.add("mb-2");

                    const senderClass = msg.sender === currentUser ? "text-end" : "text-start";
                    messageDiv.classList.add(senderClass);

                    messageDiv.innerHTML = `
                        <div class="p-2 rounded ${msg.sender === currentUser ? 'bg-primary text-white' : 'bg-light'}">
                            <strong>${msg.sender}</strong><br>
                            ${msg.message}
                            <div class="small text-muted text-end">${msg.timestamp}</div>
                        </div>
                    `;
                    chatBox.appendChild(messageDiv);
                });
                chatBox.scrollTop = chatBox.scrollHeight;
            });
    }

    // Send new message
    chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message) return;

        fetch("/send_message", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ booking_id: bookingId, message: message }),
        })
            .then(res => res.json())
            .then(() => {
                messageInput.value = "";
                loadMessages();
            });
    });

    // Refresh messages every few seconds
    loadMessages();
    setInterval(loadMessages, 5000);
});