// Wait for the DOM to fully load before adding event listeners
document.addEventListener("DOMContentLoaded", () => {
    // Get references to the form, input field, and response container
    const form = document.querySelector("#input-form"); // The form element
    const inputField = document.querySelector("#user-input"); // User input text area
    const responseContainer = document.querySelector("#response-container"); // Div for responses

    // Add an event listener to the form for the "submit" event
    form.addEventListener("submit", async (e) => {
        e.preventDefault(); // Prevent the default form submission behavior

        const userInput = inputField.value.trim(); // Get and trim user input
        responseContainer.innerHTML = "Processing..."; // Show a loading message

        if (!userInput) {
            responseContainer.innerHTML = "Please enter a message."; // Handle empty input
            return;
        }

        try {
            // Send the user's input to the server via a POST request to /chat
            const response = await fetch("/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ input: userInput }), // Pass user input in the request body
            });

            // Parse the server's JSON response
            const data = await response.json();

            // Display the server's response in the container
            if (data.response) {
                responseContainer.innerHTML = data.response;
            } else {
                responseContainer.innerHTML = "Error: No response from the server.";
            }
        } catch (error) {
            // Handle network or server errors
            responseContainer.innerHTML = `Error: ${error.message}`;
        }
    });
});
