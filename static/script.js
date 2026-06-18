const SUBMIT_LABEL = "TRACK PRODUCT";

function scrollFunction() {
  const mybutton = document.getElementById("button");
  if (!mybutton) {
    return;
  }
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

function showLoading() {
  const submitButton = document.querySelector('button[type="submit"]');
  if (!submitButton) {
    return;
  }
  submitButton.disabled = true;
  submitButton.textContent = "Processing...";
}

function hideLoading() {
  const submitButton = document.querySelector('button[type="submit"]');
  if (!submitButton) {
    return;
  }
  submitButton.disabled = false;
  submitButton.textContent = SUBMIT_LABEL;
}

function showError(message) {
  const errorDiv = document.getElementById("error-message");
  if (!errorDiv) {
    return;
  }
  errorDiv.textContent = message;
  errorDiv.style.display = "block";
  setTimeout(() => {
    errorDiv.style.display = "none";
  }, 15000);
}

function showSuccess(message) {
  const successDiv = document.getElementById("success-message");
  if (!successDiv) {
    return;
  }
  successDiv.textContent = message;
  successDiv.style.display = "block";
  setTimeout(() => {
    successDiv.style.display = "none";
  }, 10000);
}

async function readJsonResponse(response) {
  const text = await response.text();
  if (!text) {
    if (response.status === 502 || response.status === 504) {
      throw new Error(
        "Server timed out (Render free tier). Wait 30 seconds and try again."
      );
    }
    throw new Error("Empty response from server. Try again in a moment.");
  }
  try {
    return JSON.parse(text);
  } catch {
    throw new Error("Unexpected server response. Try again.");
  }
}

document.addEventListener("DOMContentLoaded", function () {
  window.addEventListener("scroll", scrollFunction);

  const form = document.getElementById("combinedForm");
  if (!form) {
    return;
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    showLoading();

    const recipient_email = document.getElementById("email").value.trim();
    const productLink = document.getElementById("productLink").value.trim();

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 28000);

      try {
        const response = await fetch("/track-product", {
          signal: controller.signal,
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            recipient_email: recipient_email,
            productLink: productLink,
          }),
        });

        const data = await readJsonResponse(response);

        if (!response.ok) {
          throw new Error(data.error || "Error tracking product");
        }

        const productDetails = data.product;
        const priceLine =
          productDetails.on_sale && productDetails.original_price
            ? `Was ${productDetails.original_price} → Now ${productDetails.current_price} (On sale!)`
            : `Price: ${productDetails.price} · Not on sale`;
        const successMessage = `Tracking started! Product: ${productDetails.name} ${priceLine} First email arriving shortly. Daily updates at 3:23 PM.`;
        showSuccess(successMessage);
        event.target.reset();
      } finally {
        clearTimeout(timeoutId);
      }
    } catch (error) {
      console.error("Error:", error);
      const message =
        error.name === "AbortError"
          ? "Request timed out. The server may be waking up — wait 30 seconds and try again."
          : error.message ||
            "Request failed. If this is the live site, wait a moment and try again.";
      showError(message);
    } finally {
      hideLoading();
    }
  });

  const dropdown = document.querySelector(".dropdown");
  const dropdownContent = document.querySelector(".dropdown-content");
  const aboutUs = document.querySelector(".about-us");

  if (aboutUs && dropdown && dropdownContent) {
    aboutUs.addEventListener("click", function (e) {
      e.stopPropagation();
      dropdownContent.classList.toggle("show");
    });

    document.addEventListener("click", function (e) {
      if (!dropdown.contains(e.target)) {
        dropdownContent.classList.remove("show");
      }
    });

    dropdownContent.addEventListener("click", function (e) {
      e.stopPropagation();
    });
  }
});
