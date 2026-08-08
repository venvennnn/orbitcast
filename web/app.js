const API = window.ORBITCAST_API || "https://api-13d-8000.sea1.zerops.app";

const stageClass = {
  queued: "border-sand/30 text-sand/70",
  researching: "border-warn text-warn stage-pulse",
  writing: "border-warn text-warn stage-pulse",
  voicing: "border-warn text-warn stage-pulse",
  publishing: "border-warn text-warn stage-pulse",
  published: "border-mint text-mint",
  completed: "border-mint text-mint",
  failed: "border-bad text-bad",
  skipped: "border-sand/40 text-sand/50",
};

function chip(stage, status) {
  const label = status === "completed" ? "published" : (stage || status || "—");
  const cls = stageClass[label] || stageClass[status] || "border-line text-sand/60";
  return `<span class="chip ${cls}">${label}</span>`;
}

function feedUrl(slug) {
  return `${API}/feed/${slug}.xml`;
}

async function copy(text) {
  await navigator.clipboard.writeText(text);
}

async function loadMetrics() {
  const m = await fetch(`${API}/metrics`).then((r) => r.json());
  const el = document.getElementById("metrics");
  el.innerHTML = [
    `queue ${m.queue_depth}`,
    `feeds ${m.active_feeds}`,
    `episodes ${m.episodes_completed}/${m.episodes_total}`,
    `failed ${m.episodes_failed}`,
    `skipped ${m.episodes_skipped}`,
    `processing ${m.episodes_processing}`,
  ]
    .map((t) => `<span class="border border-line px-2 py-1">${t}</span>`)
    .join("");
}

async function loadFeeds() {
  const feeds = await fetch(`${API}/feeds`).then((r) => r.json());
  const root = document.getElementById("feeds");
  if (!feeds.length) {
    root.innerHTML = `<p class="text-sand/50 font-mono text-sm">No feeds yet — create one above.</p>`;
    return;
  }

  const cards = await Promise.all(
    feeds.map(async (f) => {
      const detail = await fetch(`${API}/feeds/${f.id}`).then((r) => r.json());
      const episodes = detail.episodes || [];
      const latest = episodes[0];
      const rss = feedUrl(f.slug);
      const epRows = episodes
        .slice(0, 6)
        .map((e) => {
          const retry =
            e.status === "failed" || e.status === "skipped"
              ? `<button data-retry="${e.id}" class="underline text-bad/90 text-xs">retry</button>`
              : "";
          return `<li class="flex flex-wrap items-center gap-2 py-1 border-b border-line/60 last:border-0">
            ${chip(e.stage, e.status)}
            <span class="text-sm">${e.title || "Untitled"}</span>
            ${retry}
            ${e.error ? `<span class="text-xs text-bad/80 font-mono w-full">${e.error}</span>` : ""}
          </li>`;
        })
        .join("");

      return `<article class="border border-line bg-panel/60 p-4">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 class="text-xl font-semibold">${f.title}</h3>
            <p class="text-sm text-sand/60 mt-1 max-w-xl">${f.topic_prompt}</p>
            <p class="font-mono text-xs text-sand/40 mt-2">slug ${f.slug} · every ${f.schedule_minutes}m · ${f.episode_count} episodes</p>
          </div>
          <div class="flex flex-col items-end gap-2">
            ${chip(f.latest_stage, f.latest_status)}
            <button data-copy="${rss}" class="font-mono text-xs border border-mint text-mint px-2 py-1 hover:bg-mint/10">Copy RSS</button>
            <button data-refresh="${f.id}" class="font-mono text-xs border border-line px-2 py-1 hover:border-sand/50">Refresh (force ep)</button>
          </div>
        </div>
        <ul class="mt-4">${epRows || '<li class="text-sand/40 text-sm">No episodes yet</li>'}</ul>
        ${latest?.audio_url ? `<audio class="mt-3 w-full" controls src="${latest.audio_url}"></audio>` : ""}
      </article>`;
    })
  );

  root.innerHTML = cards.join("");

  root.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await copy(btn.dataset.copy);
      btn.textContent = "Copied";
      setTimeout(() => (btn.textContent = "Copy RSS"), 1200);
    });
  });
  root.querySelectorAll("[data-refresh]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      await fetch(`${API}/feeds/${btn.dataset.refresh}/refresh`, { method: "POST" });
      btn.disabled = false;
      await refresh();
    });
  });
  root.querySelectorAll("[data-retry]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await fetch(`${API}/episodes/${btn.dataset.retry}/retry`, { method: "POST" });
      await refresh();
    });
  });
}

async function refresh() {
  try {
    await Promise.all([loadMetrics(), loadFeeds()]);
  } catch (err) {
    console.error(err);
    document.getElementById("form-status").textContent = `API error: ${err.message}`;
  }
}

document.getElementById("create-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = {
    title: fd.get("title"),
    topic_prompt: fd.get("topic_prompt"),
    schedule_minutes: Number(fd.get("schedule_minutes") || 60),
  };
  const status = document.getElementById("form-status");
  status.textContent = "Creating…";
  const res = await fetch(`${API}/feeds`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    status.textContent = `Failed: ${await res.text()}`;
    return;
  }
  const feed = await res.json();
  status.textContent = `Created ${feed.slug} — episode queued`;
  e.target.reset();
  await refresh();
});

refresh();
setInterval(refresh, 2000);
