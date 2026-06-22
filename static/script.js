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
  }, 12000);
}

function setServerStatus(message, visible) {
  const statusDiv = document.getElementById("server-status");
  const submitButton = document.querySelector('button[type="submit"]');
  if (!statusDiv) {
    return;
  }
  statusDiv.textContent = message;
  statusDiv.style.display = visible ? "block" : "none";
  if (submitButton) {
    submitButton.disabled = visible;
  }
}

async function readJsonResponse(response) {
  const text = await response.text();
  if (!text) {
    if (response.status === 502 || response.status === 504) {
      throw new Error(
        "Server timed out. Refresh the page, wait for the server to start, then try again."
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

async function warmUpServer() {
  setServerStatus(
    "Starting server (first visit can take up to a minute on free hosting)...",
    true
  );

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 90000);

  try {
    const response = await fetch("/health", { signal: controller.signal });
    if (!response.ok) {
      throw new Error("Server not ready");
    }
    setServerStatus("", false);
    const submitButton = document.querySelector('button[type="submit"]');
    if (submitButton) {
      submitButton.disabled = false;
    }
  } catch {
    setServerStatus(
      "Server is still waking up — you can try submitting, or refresh in 30 seconds.",
      false
    );
  } finally {
    clearTimeout(timeoutId);
  }
}

document.addEventListener("DOMContentLoaded", function () {
  window.addEventListener("scroll", scrollFunction);
  warmUpServer();

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
      const response = await fetch("/track-product", {
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

      if (response.status === 202 || data.async) {
        const productLine = data.product
          ? ` Product: ${data.product.name} (${data.product.price || data.product.current_price}).`
          : "";
        showSuccess(
          `${data.message}${productLine} Daily updates at 3:23 PM. Check spam if needed.`
        );
        event.target.reset();
        return;
      }

      if (!response.ok) {
        throw new Error(data.error || "Error tracking product");
      }

      const productDetails = data.product;
      const priceLine =
        productDetails.on_sale && productDetails.original_price
          ? `Was ${productDetails.original_price} → Now ${productDetails.current_price} (On sale!)`
          : `Price: ${productDetails.price} · Not on sale`;
      showSuccess(
        `Email sent! Product: ${productDetails.name} ${priceLine} Daily updates at 3:23 PM.`
      );
      event.target.reset();
    } catch (error) {
      console.error("Error:", error);
      showError(
        error.message ||
          "Request failed. Refresh the page, wait for the server to start, then try again."
      );
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
