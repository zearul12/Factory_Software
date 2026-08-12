document.addEventListener("DOMContentLoaded", function () {
    const userIdInput = document.getElementById("userId");
    const passwordInput = document.getElementById("password");
    const togglePassword = document.getElementById("togglePassword");

    // ইউজার আইডিতে এন্টার দিলে পাসওয়ার্ড ফিল্ডে যাবে
    userIdInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
            e.preventDefault(); 
            passwordInput.focus();
        }
    });

    // পাসওয়ার্ড দেখা এবং লুকানোর অপশন
    togglePassword.addEventListener("click", function () {
        const type = passwordInput.getAttribute("type") === "password" ? "text" : "password";
        passwordInput.setAttribute("type", type);
        
        // আইকন পরিবর্তন
        this.classList.toggle("fa-eye");
        this.classList.toggle("fa-eye-slash");
    });
});