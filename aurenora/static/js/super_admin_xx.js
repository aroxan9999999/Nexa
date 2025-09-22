// static/js/super_admin_xx.js
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    // === 0) перенести скрытый контейнер ПЕРЕД admin-формой (чтобы блок был сверху) ===
    const hiddenFormContainer = document.querySelector("#hidden-form-container");
    const changelistForm = document.querySelector("#changelist-form"); // внешняя форма Django admin

    if (!hiddenFormContainer || !changelistForm) {
      console.error("Не найден #hidden-form-container или #changelist-form");
      return;
    }
    if (document.querySelector(".custom-form-container.module")) {
      // уже инициализировано (на всякий случай)
      return;
    }

    const formContainer = document.createElement("div");
    formContainer.className = "custom-form-container module";

    // переносим детей (НЕ innerHTML, чтобы не терять id/обработчики)
    while (hiddenFormContainer.firstChild) {
      formContainer.appendChild(hiddenFormContainer.firstChild);
    }
    hiddenFormContainer.remove();

    // вставляем блок СВЕРХУ, до таблицы пользователей
    changelistForm.parentNode.insertBefore(formContainer, changelistForm);
    formContainer.style.display = "block";

    // подпись «Пользователи» сразу после блока
    if (!document.querySelector(".compact-description-container")) {
      const descriptionContainer = document.createElement("div");
      descriptionContainer.className = "compact-description-container";
      const header = document.createElement("div");
      header.className = "compact-description-header";
      header.textContent = "Пользователи";
      descriptionContainer.appendChild(header);
      formContainer.insertAdjacentElement("afterend", descriptionContainer);
    }

    // === 1) табы ===
    const root = document.querySelector(".custom-form-container.module");
    if (!root) return;

    const forms = Array.from(root.querySelectorAll(".form-box"));
    const tabs = Array.from(root.querySelectorAll(".form-tab"));

    function showForm(targetId) {
      forms.forEach((box) => (box.style.display = box.id === targetId ? "block" : "none"));
      tabs.forEach((t) => t.classList.toggle("active", t.dataset.target === targetId));
    }
    tabs.forEach((tab) => tab.addEventListener("click", () => {
      const target = tab.dataset.target;
      if (target) showForm(target);
    }));
    showForm("msg-form");

    // === 2) кастом для file input ===
    const fileInputs = Array.from(root.querySelectorAll("input[type='file']"));
    fileInputs.forEach((fileInput, idx) => {
      if (fileInput.dataset.enhanced === "1") return;
      if (!fileInput.id) fileInput.id = `id_file_auto_${idx}`;

      const fileLabel = document.createElement("label");
      fileLabel.htmlFor = fileInput.id;
      fileLabel.className = "file-label";
      fileLabel.textContent = "Выбрать файл";

      const fileNameDisplay = document.createElement("span");
      fileNameDisplay.className = "file-name-display";
      fileNameDisplay.id = `file-name-${idx}`;
      fileNameDisplay.textContent = "Файл не выбран";
      fileNameDisplay.style.color = "red";

      fileInput.parentNode.insertBefore(fileLabel, fileInput);
      fileInput.parentNode.insertBefore(fileNameDisplay, fileInput.nextSibling);

      fileInput.addEventListener("change", function () {
        if (this.files && this.files.length > 0) {
          fileNameDisplay.textContent = this.files[0].name;
          fileNameDisplay.style.color = "#00ff00";
        } else {
          fileNameDisplay.textContent = "Файл не выбран";
          fileNameDisplay.style.color = "red";
        }
      });

      fileInput.dataset.enhanced = "1";
    });

    // === 3) хелперы ===
    function showNotification(message, isSuccess = true) {
      const el = document.createElement("div");
      el.style.cssText = "position:fixed;top:20px;right:20px;padding:15px;border-radius:5px;color:#fff;z-index:10000;font-weight:bold;box-shadow:0 4px 6px rgba(0,0,0,.1)";
      el.style.backgroundColor = isSuccess ? "#4CAF50" : "#F44336";
      el.textContent = message;
      document.body.appendChild(el);
      setTimeout(() => { el.style.transition = "opacity .5s"; el.style.opacity = "0"; setTimeout(() => el.remove(), 500); }, 5000);
    }

    async function postJSON(url, payload, useJson = true) {
      const opts = {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest", "X-CSRFToken": getCookie("csrftoken") },
        credentials: "same-origin",
      };
      if (useJson) {
        opts.headers["Content-Type"] = "application/json";
        opts.body = JSON.stringify(payload);
      } else {
        opts.body = payload; // FormData
      }

      const resp = await fetch(url, opts);
      const ct = resp.headers.get("content-type") || "";
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(`HTTP ${resp.status}: ${text.slice(0, 300)}`);
      }
      if (!ct.includes("application/json")) {
        const text = await resp.text();
        throw new Error(`Not JSON (content-type=${ct}): ${text.slice(0, 300)}`);
      }
      return await resp.json();
    }

    function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === name + "=") {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    }

    // === 4) отправка Telegram (multipart) ===
    const telegramForm = root.querySelector("#custom-form-msg");
    if (telegramForm) {
      telegramForm.addEventListener("submit", function (e) {
        e.preventDefault();
        const submit = telegramForm.querySelector('button[type="submit"]');
        const originalText = submit.textContent;
        submit.textContent = "Отправка...";
        submit.disabled = true;

        const fd = new FormData(telegramForm);

        // API ждёт button_text, а в форме поле называется button_x
        if (!fd.get("button_text") && fd.get("button_x")) {
          fd.append("button_text", fd.get("button_x"));
        }

        postJSON("/api/send-telegram/", fd, false)
          .then((data) => {
            if (data.success) {
              showNotification(`Telegram: успешно отправлено ${data.sent_count} из ${data.total_count}`, true);
            } else {
              showNotification("Ошибка при отправке Telegram: " + (data.error || ""), false);
            }
          })
          .catch((err) => {
            console.error(err);
            showNotification("Ошибка сети при отправке Telegram: " + err.message, false);
          })
          .finally(() => {
            submit.textContent = originalText;
            submit.disabled = false;
          });
      });
    }

    // === 5) отправка Email (JSON) ===
    const emailForm = root.querySelector("#custom-form-email");
    if (emailForm) {
      emailForm.addEventListener("submit", function (e) {
        e.preventDefault();
        const submit = emailForm.querySelector('button[type="submit"]');
        const originalText = submit.textContent;
        submit.textContent = "Отправка...";
        submit.disabled = true;

        const fd = new FormData(emailForm);
        const payload = {
          country: fd.get("country"),
          subject: fd.get("subject"),
          message: fd.get("message"),
        };

        postJSON("/api/send-email/", payload, true)
          .then((data) => {
            if (data.success) {
              showNotification(`Email: успешно отправлено ${data.sent_count} из ${data.total_count}`, true);
            } else {
              showNotification("Ошибка при отправке Email: " + (data.error || ""), false);
            }
          })
          .catch((err) => {
            console.error(err);
            showNotification("Ошибка сети при отправке Email: " + err.message, false);
          })
          .finally(() => {
            submit.textContent = originalText;
            submit.disabled = false;
          });
      });
    }

    // === 6) отправка SMS (JSON) ===
    const smsForm = root.querySelector("#custom-form-phone");
    if (smsForm) {
      smsForm.addEventListener("submit", function (e) {
        e.preventDefault();
        const submit = smsForm.querySelector('button[type="submit"]');
        const originalText = submit.textContent;
        submit.textContent = "Отправка...";
        submit.disabled = true;

        const fd = new FormData(smsForm);
        const payload = {
          country: fd.get("country"),
          text: fd.get("text"),
          sender_name: fd.get("sender_name"),
        };

        postJSON("/api/send-sms/", payload, true)
          .then((data) => {
            if (data.success) {
              showNotification(`SMS: успешно отправлено ${data.sent_count} из ${data.total_count}`, true);
            } else {
              showNotification("Ошибка при отправке SMS: " + (data.error || ""), false);
            }
          })
          .catch((err) => {
            console.error(err);
            showNotification("Ошибка сети при отправке SMS: " + err.message, false);
          })
          .finally(() => {
            submit.textContent = originalText;
            submit.disabled = false;
          });
      });
    }
  });
})();
