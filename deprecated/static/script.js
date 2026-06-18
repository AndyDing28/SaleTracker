function scrollToContent() {
  const contentElement = document.querySelector("#content");
  contentElement.scrollIntoView({ behavior: "smooth" });
}

let mybutton = document.getElementById("myBtn");

window.onscroll = function () {
  scrollFunction();
};

function scrollFunction() {
  if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
    mybutton.style.display = "block";
  } else {
    mybutton.style.display = "none";
  }
}

function topFunction() {
  document.body.scrollTo({ top: 0, behavior: "smooth" });
  document.documentElement.scrollTo({ top: 0, behavior: "smooth" });
}

// Show loading state
function showLoading() {
  const submitButton = document.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  submitButton.innerHTML = 'Processing...';
}

// Hide loading state
function hideLoading() {
  const submitButton = document.querySelector('button[type="submit"]');
  submitButton.disabled = false;
  submitButton.innerHTML = 'Submit';
}

// Show error message
function showError(message) {
  const errorDiv = document.getElementById('error-message');
  errorDiv.textContent = message;
  errorDiv.style.display = 'block';
  setTimeout(() => {
    errorDiv.style.display = 'none';
  }, 5000);
}

// Show success message
function showSuccess(message) {
  const successDiv = document.getElementById('success-message');
  successDiv.textContent = message;
  successDiv.style.display = 'block';
  setTimeout(() => {
    successDiv.style.display = 'none';
  }, 10000); // milliseconds — 10000 = 10 seconds
}

document
  .getElementById("combinedForm")
  .addEventListener("submit", async function (event) {
    event.preventDefault();
    showLoading();

    const recipient_email = document.getElementById("email").value;
    const productLink = document.getElementById("productLink").value;

    try {
      // First update the product link
      const updateResponse = await fetch("/update-product-link", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ productLink: productLink }),
      });

      const updateData = await updateResponse.json();

      if (!updateResponse.ok) {
        throw new Error(updateData.error || "Error updating product link");
      }

      // Then schedule the email
      const emailResponse = await fetch("/schedule-email", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ recipient_email: recipient_email }),
      });

      const emailData = await emailResponse.json();

      if (!emailResponse.ok) {
        throw new Error(emailData.error || "Error scheduling email");
      }

      // Show success message with product details
      const productDetails = emailData.product;
      const priceLine = productDetails.on_sale && productDetails.original_price
        ? `Was ${productDetails.original_price} → Now ${productDetails.current_price} (On sale!)`
        : `Price: ${productDetails.price} · Not on sale`;
      const successMessage = `
        Email sent successfully!
        Product: ${productDetails.name}
        ${priceLine}
        You will now receive daily updates at 3:23 PM.
      `;
      showSuccess(successMessage);
      event.target.reset();
    } catch (error) {
      console.error("Error:", error);
      showError(error.message);
    } finally {
      hideLoading();
    }
  });

// Dropdown functionality
document.addEventListener('DOMContentLoaded', function() {
    const dropdown = document.querySelector('.dropdown');
    const dropdownContent = document.querySelector('.dropdown-content');
    const aboutUs = document.querySelector('.about-us');

    // Toggle dropdown on click
    aboutUs.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdownContent.classList.toggle('show');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!dropdown.contains(e.target)) {
            dropdownContent.classList.remove('show');
        }
    });

    // Prevent dropdown from closing when clicking inside it
    dropdownContent.addEventListener('click', function(e) {
        e.stopPropagation();
    });
});
