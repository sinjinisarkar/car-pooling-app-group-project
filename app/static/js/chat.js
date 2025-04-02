
// Notification Logic
let dismissedBookingIds = new Set();
function checkForNewMessages() {
    fetch('/check_new_messages')
        .then(response => response.json())
        .then(data => {
            if (data.new && Array.isArray(data.messages)) {
                const stack = document.getElementById('chat-notification-stack');

                data.messages.forEach(msg => {
                    // If already dismissed, skip
                    if (dismissedBookingIds.has(msg.booking_id)) return;

                    // If already shown, skip
                    if (document.getElementById(`notif-${msg.booking_id}`)) return;

                    const banner = document.createElement("div");
                    banner.id = `notif-${msg.booking_id}`;
                    banner.className = "chat-banner shadow-sm rounded p-2 bg-light border mb-2";
                    banner.style.backgroundColor = "#f8f9fa";
                    banner.style.color = "#212529";
                    banner.style.minWidth = "250px";

                    banner.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                New message from <strong>${msg.sender}</strong><br>
                                <a href="/chat/${msg.booking_id}" class="open-chat" data-bid="${msg.booking_id}" data-mid="${msg.message_id}">Open Chat</a>
                            </div>
                            <i class="fas fa-xmark close-icon" style="cursor: pointer; margin-left: 10px;"></i>
                        </div>
                    `;

                    banner.querySelector(".close-icon").addEventListener("click", () => {
                        banner.remove();
                    
                        // Send a POST request to mark the message as seen in the database
                        fetch(`/mark_message_seen/${msg.message_id}`, {
                            method: "POST"
                        });
                    
                        dismissedBookingIds.add(msg.booking_id);  
                    });

                    stack.appendChild(banner);
                });
            }
        })
        .catch(error => console.error('Error checking new messages:', error));
}
setInterval(checkForNewMessages, 10000);

// Event listener to see if the user opens the chat then the notification wont be shown again
document.addEventListener("click", function (e) {
    if (e.target.classList.contains("open-chat")) {
        const bid = parseInt(e.target.getAttribute("data-bid"));
        const mid = parseInt(e.target.getAttribute("data-mid"));

        dismissedBookingIds.add(bid);

        // Mark message seen in the database
        fetch(`/mark_message_seen/${mid}`, {
            method: "POST"
        });

        const banner = document.getElementById(`notif-${bid}`);
        if (banner) banner.remove();
    }
});

// Chat Page Logic 
document.addEventListener("DOMContentLoaded", () => {
    // Extract bookingId and currentUser from HTML data attributes
    const chatBox = document.getElementById("chat-box");
    const chatForm = document.getElementById("chat-form");
    const messageInput = document.getElementById("message-input");

     // Only run the chat logic if we're on the chat page
     if (!chatBox || !chatForm || !messageInput) return;

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

