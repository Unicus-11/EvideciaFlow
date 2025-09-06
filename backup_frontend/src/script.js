const fileInput = document.getElementById("fileInput");
const uploadBtn = document.getElementById("uploadBtn");
const statusDiv = document.getElementById("status");

uploadBtn.addEventListener("click", () => {
    if (!fileInput.files || fileInput.files.length === 0) {
        statusDiv.textContent = "Please select a file first!";
        statusDiv.style.color = "red";
        return;
    }

    const file = fileInput.files[0];
    console.log("Selected file:", file.name);
    statusDiv.textContent = `Selected file: ${file.name}`;
    statusDiv.style.color = "green";

    // Example: send file to backend (replace URL with your backend endpoint)
    /*
    const formData = new FormData();
    formData.append("file", file);

    fetch("http://localhost:5000/upload", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        console.log("Upload success:", data);
        statusDiv.textContent = "Upload successful!";
    })
    .catch(err => {
        console.error("Upload failed:", err);
        statusDiv.textContent = "Upload failed!";
        statusDiv.style.color = "red";
    });
    */
});

