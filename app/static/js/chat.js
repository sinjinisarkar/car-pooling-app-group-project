
// Notification Logic
let dismissedMessageIds = new Set();
function checkForNewMessages() {
    fetch('/check_new_messages')
        .then(response => response.json())
        .then(data => {
            if (data.new && Array.isArray(data.messages)) {
                const stack = document.getElementById('chat-notification-stack');

                data.messages.forEach(msg => {
                    // If already dismissed then skip
                    if (dismissedMessageIds.has(msg.message_id)) return;

                    // If already shown then skip
                    if (document.getElementById(`notif-${msg.message_id}`)) return;

                    const banner = document.createElement("div");
                    banner.id = `notif-${msg.message_id}`;
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
                        }).then(() => {
                            banner.remove();
                            dismissedMessageIds.add(msg.message_id);
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
        fetch(`/mark_message_seen/${msg.message_id}`, {
            method: "POST"
        }).then(() => {
            banner.remove();
            dismissedMessageIds.add(msg.message_id);
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

    // You can store this in a hidden element via Jinja in future
    const currentUser = document.querySelector("meta[name='current-user']").content;

    // Load existing messages
    function loadMessages() {
        fetch(`/get_messages/${bookingId}`)
            .then(res => res.json())
            .then(data => {
                chatBox.innerHTML = "";
    
                data.forEach(item => {
                    const messageDiv = document.createElement("div");
                    messageDiv.classList.add("mb-2");
    
                    if (item.type === "message") {
                        const isSender = item.sender === currentUser;
                        const wrapperClass = isSender ? "justify-content-end" : "justify-content-start";
                    
                        messageDiv.className = `d-flex ${wrapperClass} mb-3`;
                    
                        messageDiv.innerHTML = `
                            <div class="message-bubble ${isSender ? 'sent-message' : 'received-message'}">
                                <div>${item.message}</div>
                                <div class="timestamp">${item.timestamp}</div>
                            </div>
                        `;
                    } else if (item.type === "proposal") {
                        const isSender = item.sender === currentUser;
                        const borderClass = isSender ? "border-primary" : "border-warning";
    
                        let proposalHTML = `
                            <div class="p-2 border ${borderClass} rounded bg-white">
                                <strong>📌 Edit Proposal from ${item.sender}</strong><br>
                                <ul style="margin-bottom: 4px;">
                                    ${item.pickup ? `<li>Pickup Point: ${item.pickup}</li>` : ""}
                                    ${item.time ? `<li>Time: ${item.time}</li>` : ""}
                                    ${item.cost ? `<li>Cost: £${item.cost}</li>` : ""}
                                </ul>
                                <div class="small text-muted">${item.timestamp}</div>
                        `;
    
                        if (!isSender && item.status === "pending") {
                            proposalHTML += `
                                <button class="btn btn-sm btn-success mt-1 me-1 accept-proposal" data-id="${item.id}">Accept</button>
                                <button class="btn btn-sm btn-danger mt-1 reject-proposal" data-id="${item.id}">Reject</button>
                            `;
                        } else {
                            proposalHTML += `<span class="badge bg-secondary">${item.status.toUpperCase()}</span>`;
                        }
    
                        proposalHTML += `</div>`;
                        messageDiv.innerHTML = proposalHTML;
                    }
    
                    chatBox.appendChild(messageDiv);

                    // auto-mark messages as seen when loading chat
                    if (item.type === "message" && item.sender !== currentUser) {
                        fetch(`/mark_message_seen/${item.id}`, {
                            method: "POST"
                        });
                    }
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

    // Handle Accept/Reject of Proposals 
    document.addEventListener("click", (e) => {
        if (e.target.classList.contains("accept-proposal") || e.target.classList.contains("reject-proposal")) {
            const proposalId = e.target.getAttribute("data-id");
            const action = e.target.classList.contains("accept-proposal") ? "accept" : "reject";

            fetch("/respond_proposal", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ proposal_id: proposalId, action: action }),
            })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    loadMessages();  // Refresh to update status
                } else {
                    alert("Error processing proposal.");
                }
            });
        }
    });

    // Refresh messages every few seconds
    loadMessages();
    setInterval(loadMessages, 5000);
});

