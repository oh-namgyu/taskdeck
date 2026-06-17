"use strict";

// Column order; left-to-right moves walk this list.
const STATUSES = ["todo", "doing", "review", "done"];

const filters = { project: "", date: "" };

const api = {
  list(query) {
    return fetch("/api/tasks" + query).then(ok).then((r) => r.json()).then((d) => d.tasks);
  },
  create(data) {
    return send("/api/tasks", "POST", data);
  },
  update(id, patch) {
    return send("/api/tasks/" + id, "PUT", patch);
  },
  remove(id) {
    return fetch("/api/tasks/" + id, { method: "DELETE" }).then(ok);
  },
};

function ok(res) {
  if (!res.ok) throw new Error(res.status + " " + res.statusText);
  return res;
}

function send(url, method, body) {
  return fetch(url, {
    method: method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(ok);
}

function fail(err) {
  console.error(err);
  window.alert("Request failed: " + err.message);
}

// --- DOM helpers (no inline styles; classes only) ---
function el(tag, cls) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  return node;
}

function badge(text, extra) {
  const b = el("span", "badge" + (extra ? " " + extra : ""));
  b.textContent = text;
  return b;
}

function iconButton(label, title, handler) {
  const b = el("button", "btn btn-icon");
  b.type = "button";
  b.textContent = label;
  b.title = title;
  b.setAttribute("aria-label", title);
  b.addEventListener("click", handler);
  return b;
}

// --- Rendering ---
function buildQuery() {
  const params = new URLSearchParams();
  if (filters.project) params.set("project", filters.project);
  if (filters.date) params.set("date", filters.date);
  const qs = params.toString();
  return qs ? "?" + qs : "";
}

function render(tasks) {
  const buckets = { todo: [], doing: [], review: [], done: [] };
  tasks.forEach((t) => (buckets[t.status] || buckets.todo).push(t));

  STATUSES.forEach((status) => {
    const list = document.querySelector('.kanban-items[data-status="' + status + '"]');
    const count = document.querySelector('.kanban-count[data-status="' + status + '"]');
    list.innerHTML = "";
    buckets[status].forEach((t) => list.appendChild(cardElement(t)));
    count.textContent = String(buckets[status].length);
  });

  document.getElementById("progress").textContent =
    buckets.done.length + "/" + tasks.length + " done";
}

function cardElement(task) {
  const card = el("div", "kanban-card");
  card.dataset.id = String(task.id);

  const title = el("div", "kanban-card-title");
  title.textContent = task.title;
  card.appendChild(title);

  const tags = task.tags || [];
  if (task.project || task.due_date || tags.length) {
    const meta = el("div", "kanban-card-meta");
    if (task.project) meta.appendChild(badge(task.project));
    if (task.due_date) meta.appendChild(badge("📅 " + task.due_date, "badge-tag"));
    tags.forEach((tag) => meta.appendChild(badge(tag, "badge-tag")));
    card.appendChild(meta);
  }

  card.appendChild(cardActions(task));
  return card;
}

function cardActions(task) {
  const row = el("div", "card-actions");
  const idx = STATUSES.indexOf(task.status);
  if (idx > 0) {
    row.appendChild(iconButton("◀", "move left", () => move(task, idx - 1)));
  }
  if (idx < STATUSES.length - 1) {
    row.appendChild(iconButton("▶", "move right", () => move(task, idx + 1)));
  }
  row.appendChild(iconButton("✎", "edit", () => edit(task)));
  row.appendChild(iconButton("✕", "delete", () => removeTask(task)));
  return row;
}

// --- Actions (each surfaces request failures instead of swallowing them) ---
async function move(task, toIdx) {
  try {
    await api.update(task.id, { status: STATUSES[toIdx] });
    await refresh();
  } catch (e) {
    fail(e);
  }
}

async function edit(task) {
  const next = window.prompt("Edit task title", task.title);
  if (!next || !next.trim()) return;
  try {
    await api.update(task.id, { title: next.trim() });
    await refresh();
  } catch (e) {
    fail(e);
  }
}

async function removeTask(task) {
  if (!window.confirm('Delete "' + task.title + '"?')) return;
  try {
    await api.remove(task.id);
    await refresh();
  } catch (e) {
    fail(e);
  }
}

async function addTask() {
  const titleInput = document.getElementById("new-title");
  const projectInput = document.getElementById("new-project");
  const dueInput = document.getElementById("new-due");
  const title = titleInput.value.trim();
  if (!title) return;
  try {
    await api.create({
      title: title,
      project: projectInput.value.trim() || null,
      due_date: dueInput.value || null,
    });
    titleInput.value = "";
    dueInput.value = "";
    await refresh();
  } catch (e) {
    fail(e);
  }
}

async function refresh() {
  try {
    render(await api.list(buildQuery()));
  } catch (e) {
    fail(e);
  }
}

// --- Wiring ---
function init() {
  document.getElementById("add-btn").addEventListener("click", addTask);
  document.getElementById("new-title").addEventListener("keydown", (e) => {
    if (e.key === "Enter") addTask();
  });
  const projectFilter = document.getElementById("filter-project");
  projectFilter.addEventListener("input", () => {
    filters.project = projectFilter.value.trim();
    refresh();
  });
  const dateFilter = document.getElementById("filter-date");
  dateFilter.addEventListener("change", () => {
    filters.date = dateFilter.value;
    refresh();
  });
  refresh();
}

document.addEventListener("DOMContentLoaded", init);
