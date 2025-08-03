document.addEventListener("DOMContentLoaded", function () {
    const loginForm = document.getElementById("login-form");
    const signupForm = document.getElementById("signup-form");
    const uploadForm = document.getElementById("uploadForm");
    const fileInput = document.getElementById("fileInput");
    const predictionResult = document.getElementById("predictionResult");
    const uploadError = document.getElementById("uploadError");
    const logoutButton = document.getElementById("logoutButton");
    const signupModal = document.getElementById("success-modal");
    const modalOkButton = document.getElementById("modal-ok-button");
    const waitingMessage = document.getElementById("waitingMessage");

    const imagePreviewContainer = document.getElementById("imagePreviewContainer");
    const imagePreview = document.getElementById("imagePreview");

    //LOGIN FUNCTIONALITY
    if (loginForm) {
        loginForm.addEventListener("submit", async function (event) {
            event.preventDefault();
            const username = document.getElementById("login-username").value;
            const password = document.getElementById("login-password").value;

            const response = await fetch("/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();
            if (response.ok) {
                window.location.href = "/upload";
            } else {
                document.getElementById("login-error").innerText = data.message;
            }
        });

        //Password visibility toggle for login form
        const togglePasswordLogin = document.getElementById("toggle-password-login");
        const loginPasswordInput = document.getElementById("login-password");
        togglePasswordLogin.addEventListener("click", function () {
            if (loginPasswordInput.type === "password") {
                loginPasswordInput.type = "text";
                togglePasswordLogin.innerHTML = "Hide password"; // Open eye icon
            } else {
                loginPasswordInput.type = "password";
                togglePasswordLogin.innerHTML = "Show password"; // Eye with slash
            }
        });
    }

    //SIGNUP FUNCTIONALITY
    if (signupForm) {
        signupForm.addEventListener("submit", async function (event) {
            event.preventDefault();
            const username = document.getElementById("signup-username").value;
            const password = document.getElementById("signup-password").value;

            if (password.length < 8) {
                document.getElementById("signup-error").innerText = "Password must be at least 8 characters long.";
                return;
            }

            const response = await fetch("/signup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();
            if (response.ok) {
                signupModal.classList.add("active"); // Show modal on success
            } else {
                document.getElementById("signup-error").innerText = data.message;
            }
        });

        //Password visibility toggle for signup form
        const togglePasswordSignup = document.getElementById("toggle-password-signup");
        const signupPasswordInput = document.getElementById("signup-password");
        togglePasswordSignup.addEventListener("click", function () {
            if (signupPasswordInput.type === "password") {
                signupPasswordInput.type = "text";
                togglePasswordSignup.innerHTML = "Hide password"; // Open eye icon
            } else {
                signupPasswordInput.type = "password";
                togglePasswordSignup.innerHTML = "Show password"; // Eye with slash
            }
        });
    }

    if (modalOkButton) {
        modalOkButton.addEventListener("click", function () {
            window.location.href = "/login"; // Redirect to login page
        });
    }

    //FILE UPLOAD & PREDICTION FUNCTIONALITY
    if (uploadForm) {
        // Image Preview Feature
        fileInput.addEventListener("change", function () {
            const file = fileInput.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (e) {
                    imagePreview.src = e.target.result;
                    imagePreviewContainer.style.display = 'block'; // Show the image preview container
                };
                reader.readAsDataURL(file);
            } else {
                imagePreviewContainer.style.display = 'none'; // Hide preview if no file is selected
            }
        });

        uploadForm.addEventListener("submit", function (event) {
            event.preventDefault();

            let file = fileInput.files[0];
            if (!file) {
                uploadError.innerText = "Please select a file.";
                return;
            }

            waitingMessage.style.display = 'block';
            predictionResult.style.display = 'none';

            let formData = new FormData();
            formData.append("file", file);

            fetch("/upload", { method: "POST", body: formData })
                .then(response => response.json())
                .then(data => {
                    waitingMessage.style.display = 'none';
                    if (data.bone_type && data.result) {
                        predictionResult.innerHTML = `Bone Type: <b>${data.bone_type}</b><br>Result: <b>${data.result}</b>`;
                        predictionResult.style.display = 'block';

                        // Replace uploaded image with heatmap if fractured (Fixed)
                        if (data.result === "Fractured" && data.heatmap_image) {
                            imagePreview.src = data.heatmap_image + "?t=" + new Date().getTime(); // Force refresh
                        }
                    } else {
                        predictionResult.innerHTML = "<span style='color: red;'>Prediction failed.</span>";
                        predictionResult.style.display = 'block';
                    }
                })
                .catch(error => {
                    console.error("Error:", error);
                    waitingMessage.style.display = 'none';
                    predictionResult.innerHTML = "<span style='color: red;'>Server error occurred.</span>";
                    predictionResult.style.display = 'block';
                });
        });
    }

    if (logoutButton) {
        logoutButton.addEventListener("click", function () {
            fetch("/logout", { method: "POST" })
                .then(() => {
                    window.location.href = "/login"; // Redirect to login without pop-up
                })
                .catch(error => console.error("Logout Error:", error));
        });
    }
});
