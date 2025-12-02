(function () {
  const qs = (sel) => document.querySelector(sel);
  const drop = qs("[data-dropzone]");
  const input = qs("#fileInput");
  const status = qs("#status");
  const result = qs("#result");
  const form = qs("#uploadForm");

  const state = { file: null };

  const mkStatus = (txt, kind) => {
    status.textContent = txt;
    status.className = kind ? "status " + kind : "status";
  };
  const mkResult = (obj) => {
    if (!obj) {
      result.innerHTML = "";
      return;
    }

    if (obj.ok) {
      result.innerHTML = `
      <div class="result-box result-success">
        <strong>Subida correcta:</strong> ${escapeHtml(obj.filename)}<br>
        Guardado en: <code>${escapeHtml(obj.saved_to)}</code>
        <pre>${escapeHtml(JSON.stringify(obj.validation, null, 2))}</pre>
      </div>
    `;
    } else {
      const details = obj.details
        ? `<pre>${escapeHtml(JSON.stringify(obj.details, null, 2))}</pre>`
        : "";
      result.innerHTML = `
      <div class="result-box result-error">
        <strong>Error:</strong> ${escapeHtml(obj.error || "Error desconocido")}
        ${details}
      </div>
    `;
    }
  };

  function escapeHtml(s) {
    return String(s).replace(
      /[&<>"']/g,
      (c) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[c])
    );
  }

  function clientValidate(file) {
    const allowedExt = /\.csv$/i;
    if (!file.name || !allowedExt.test(file.name))
      return {
        ok: false,
        msg: "El nombre de archivo debe terminar en .csv",
      };
    if (
      file.type &&
      !(file.type.startsWith("text/") || file.type.includes("csv"))
    ) {
      console.warn("Tipo MIME sospechoso:", file.type);
    }
    return { ok: true };
  }

  function quickContentCheck(file) {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = String(e.target.result || "");
        const sample = text.slice(0, 8192);
        const hasComma = sample.includes(",");
        const hasSemicolon = sample.includes(";");
        const hasTab = sample.includes("\t");
        if (!(hasComma || hasSemicolon || hasTab)) {
          resolve({
            ok: false,
            msg: "No se detectó un separador común (, ; o tab). Revisa tu archivo.",
          });
        } else {
          resolve({ ok: true });
        }
      };
      reader.onerror = () =>
        resolve({
          ok: false,
          msg: "No se pudo leer el archivo en el navegador.",
        });
      reader.readAsText(file.slice(0, 8192));
    });
  }

  // manejadores declarativos
  const onFileChosen = async (file) => {
    if (!file) return;
    mkStatus("Validando archivo (cliente)...");
    const checkName = clientValidate(file);
    if (!checkName.ok) {
      mkStatus("Error: " + checkName.msg, "error");
      mkResult({ ok: false, error: checkName.msg });
      return;
    }

    const quick = await quickContentCheck(file);
    if (!quick.ok) {
      mkStatus("Error: " + quick.msg, "error");
      mkResult({ ok: false, error: quick.msg });
      return;
    }

    state.file = file;
    mkStatus(
      `${file.name} listo para subir (${Math.round(file.size / 1024)} KB)`
    );
    mkResult(null);
  };

  ["dragenter", "dragover"].forEach((ev) =>
    drop.addEventListener(ev, (e) => {
      e.preventDefault();
      drop.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((ev) =>
    drop.addEventListener(ev, (e) => {
      drop.classList.remove("dragover");
    })
  );
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if (f) {
      input.files = e.dataTransfer.files;
      onFileChosen(f);
    }
  });

  input.addEventListener("change", (e) => {
    const f = input.files && input.files[0];
    onFileChosen(f);
  });

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!state.file) {
      mkStatus("Selecciona un archivo antes de subir.", "error");
      return;
    }

    mkStatus("Subiendo...");
    const fd = new FormData();
    fd.append("file", state.file, state.file.name);

    try {
      const resp = await fetch("/", { method: "POST", body: fd });
      const json = await resp.json();
      console.log("Respuesta del servidor:", json);

      if (resp.ok && json.ok) {
        mkStatus("Subida completa ✅");

        // Mostrar sección de estado
        const taskStatusDiv = qs("#taskStatus");
        const workIdSpan = qs("#workId");

        taskStatusDiv.style.display = "block";
        workIdSpan.textContent = json.work_id;

        // Iniciar polling del estado
        startStatusPolling(json.work_id);

        result.innerHTML = `
          <div class="result-box result-success">
            <strong>Archivo subido correctamente:</strong> ${escapeHtml(state.file.name)}<br>
            <span class="muted small">El estado se actualizará automáticamente abajo</span>
          </div>
        `;
      } else {
        mkStatus("Error al subir", "error");
        mkResult(json);
      }
    } catch (err) {
      mkStatus("Error de red al subir", "error");
      mkResult({ ok: false, error: err.message || String(err) });
    }
  });

  // Función para hacer polling del estado
  let pollingInterval = null;

  function startStatusPolling(workId) {
    // Limpiar polling anterior si existe
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }

    // Hacer primera consulta inmediatamente
    updateTaskStatus(workId);

    // Consultar cada 3 segundos
    pollingInterval = setInterval(() => {
      updateTaskStatus(workId);
    }, 3000);
  }

  async function updateTaskStatus(workId) {
    try {
      const resp = await fetch(`/api/status/${workId}`);
      const data = await resp.json();

      const statusBadge = qs("#statusBadge");
      const statusMessage = qs("#statusMessage");
      const errorMessage = qs("#errorMessage");
      const downloadBtn = qs("#downloadBtn");

      // Actualizar badge de estado
      statusBadge.className = "status-badge " + data.status.toLowerCase();
      statusBadge.textContent = data.status;

      // Actualizar mensaje según el estado
      switch (data.status) {
        case "pending":
          statusMessage.textContent = "La tarea está en cola, será procesada pronto...";
          break;
        case "running":
          statusMessage.textContent = "El scraper está descargando los CSVs. Esto puede tomar varios minutos...";
          break;
        case "completed":
          statusMessage.textContent = "¡Proceso completado! Tu archivo está listo para descargar.";
          downloadBtn.href = data.download_url;
          downloadBtn.style.display = "inline-block";
          // Detener polling
          if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
          }
          break;
        case "failed":
          statusMessage.textContent = "La tarea falló durante la ejecución.";
          if (data.error) {
            errorMessage.textContent = "Error: " + data.error;
            errorMessage.style.display = "block";
          }
          // Detener polling
          if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
          }
          break;
        case "not_found":
          statusMessage.textContent = "No se encontró la tarea.";
          if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
          }
          break;
      }
    } catch (err) {
      console.error("Error al consultar estado:", err);
    }
  }

  drop.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") input.click();
  });
})();
