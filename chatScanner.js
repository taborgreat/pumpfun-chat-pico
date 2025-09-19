const { io } = require("socket.io-client");
const axios = require("axios");

// Pump.fun chat server
const SOCKET_URL = "https://livechat.pump.fun";

//token to track
const ROOM_ID = "4eGFLijrbcoLrBXtSZMPaM8qDTNcqSsAR7gaX3xrpump";

// replace with actual IP
const PICO_URL = "http://10.0.0.2/";

let mostRecentMessage = null;

const socket = io(SOCKET_URL, { transports: ["websocket"] });

socket.on("connect", () => {
    console.log("Connected to pump.fun chat server");

    socket.emit("joinRoom", { roomId: ROOM_ID });
});

socket.on("newMessage", (msg) => {
    mostRecentMessage = msg;
});


setInterval(async () => {



    if (mostRecentMessage) {
        const usernameRaw = mostRecentMessage.username || "";
        const messageRaw = mostRecentMessage.message || mostRecentMessage.text || "";

        // Sanitize
        let username = usernameRaw.length > 16 ? "Long Name" : usernameRaw;

        username = username.replace(/[^a-zA-Z0-9 ,.!]/g, "");

        let message = messageRaw.replace(/[^a-zA-Z0-9 ,.!]/g, "");


        try {
            await axios.get(PICO_URL, {
                params: { user: username, message },
            });
            console.log("Sent mostRecentMessage:", { user: username, message });
            mostRecentMessage = null; // clear after sending to prevent spam
        } catch (err) {
            console.error("Error sending mostRecentMessage:", err.message);
        }
    }
}, 5000);


socket.on("disconnect", () => {
    console.log("Disconnected from chat server");
});
