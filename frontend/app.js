const API_BASE = "http://localhost:5000/api";

async function postJSON(url, data) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data || {})
  });
  return res.json();
}

function attach(id, handler) {
  const el = document.getElementById(id);
  if (el) el.addEventListener("click", handler);
}

attach("extraction-run", async () => {
  const text = document.getElementById("extraction-input").value;
  const data = await postJSON(`${API_BASE}/extraction/run`, { text });
  document.getElementById("extraction-output").textContent = JSON.stringify(data, null, 2);
});

attach("mapping-run", async () => {
  const data = await postJSON(`${API_BASE}/mapping/run`, {});
  document.getElementById("mapping-output").textContent = JSON.stringify(data, null, 2);
});

attach("verification-run", async () => {
  const data = await postJSON(`${API_BASE}/verification/run`, {});
  document.getElementById("verification-output").textContent = JSON.stringify(data, null, 2);
});
