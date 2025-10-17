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
      if (resp.ok && json.ok) {
        mkStatus("Subida completa ✅");
        result.innerHTML = `
        <div class="result-box result-success">
          <strong>Archivo subido correctamente:</strong> ${escapeHtml(
            state.file.name
          )}<br>
          <span class="muted small">Puedes revisar el estado en <a href="/check">check</a></span>
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

  drop.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") input.click();
  });
})();
