const socket = io();

socket.on("connect", () => {
    socket.emit("join");
});

function sendMessage(receiverId) {
    const input = document.getElementById("message-input");
    if (!input) return;

    const message = input.value.trim();
    if (message === "") return;

    socket.emit("send_message", {
        receiver_id: receiverId,
        message: message
    });

    // append sender message (RIGHT)
    const container = document.getElementById("chat-messages");
    const div = document.createElement("div");
    div.classList.add("chat-message", "sent");

    const p = document.createElement("p");
    p.innerText = message;

    div.appendChild(p);
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;

    input.value = "";
}

// receive message (LEFT)
socket.on("receive_message", (data) => {
    const container = document.getElementById("chat-messages");
    if (!container) return;

    const div = document.createElement("div");
    div.classList.add("chat-message", "received");

    const p = document.createElement("p");
    p.innerText = data.message;

    div.appendChild(p);
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
});
